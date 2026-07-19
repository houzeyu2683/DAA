"""
graph_with_mcp_agents_example.py

整合前面討論過的所有東西:
1. 一個 graph，裡面有多個 node，每個 node 用 create_agent 完成特定任務
2. 每個 agent 用到的 tools 來自 MCP server，且只在 graph 建構時載入一次
   （不在每個 node 執行時重新抓）
3. tool 執行時需要的 state 相關參數（user_id, session_token）不讓 LLM 生成，
   而是用 ToolRuntime 在執行前手動從 graph state 注入進去
4. 多個 agent node 各自包成獨立命名空間的 subgraph，避免內部 node 名稱撞名

執行方式:
    pip install langgraph langchain langchain-anthropic langchain-mcp-adapters mcp
    export ANTHROPIC_API_KEY=...
    python graph_with_mcp_agents_example.py
"""
import asyncio
from typing import Annotated, TypedDict, List

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.tools import StructuredTool
from langchain.agents import create_agent
from langchain.tools import ToolRuntime
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.graph.message import add_messages
from langchain_mcp_adapters.client import MultiServerMCPClient


# 1. 外層 graph 的 state ---------------------------------------------------------
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    user_id: str
    session_token: str


# 2. 把 MCP 原始工具包成「隱藏 state 參數」的版本 -----------------------------------
def wrap_with_runtime(raw_tool) -> StructuredTool:
    """
    對 LLM 只曝露非 state 欄位；user_id / session_token 用 ToolRuntime 注入，
    在真正呼叫 MCP tool 之前手動 merge 進去。
    """

    async def _call(question: str, runtime: ToolRuntime) -> str:
        merged_args = {
            "question": question,
            "user_id": runtime.state["user_id"],
            "session_token": runtime.state["session_token"],
        }
        return await raw_tool.ainvoke(merged_args)

    return StructuredTool.from_function(
        coroutine=_call,
        name=raw_tool.name,
        description=raw_tool.description,
    )


# 3. 建立共用的 MCP client，把每個 subagent 需要的 tools 各自包裝好 --------------------
async def build_agent_nodes():
    client = MultiServerMCPClient(
        {
            "docs_server": {
                "url": "http://localhost:8000/mcp",
                "transport": "http",
            },
            "crm_server": {
                "url": "http://localhost:8001/mcp",
                "transport": "http",
            },
        }
    )

    # 只在這裡呼叫一次，之後所有 node 共用這份 tool list，不重複抓取
    all_tools = await client.get_tools()

    docs_tools = [
        wrap_with_runtime(t) for t in all_tools if t.name in ("search_docs",)
    ]
    crm_tools = [
        wrap_with_runtime(t) for t in all_tools if t.name in ("lookup_customer",)
    ]

    research_agent = create_agent(
        "claude-sonnet-4-6",
        tools=docs_tools,
        state_schema=AgentState,  # 讓 agent 認得 user_id / session_token
    )
    crm_agent = create_agent(
        "claude-sonnet-4-6",
        tools=crm_tools,
        state_schema=AgentState,
    )

    return research_agent, crm_agent


def wrap_as_subgraph(agent, *, name: str):
    """給每個 subagent 一個獨立命名空間，避免內部 node 名稱互相撞名。"""
    return StateGraph(MessagesState).add_node(name, agent).compile()


# 4. 組裝外層 graph --------------------------------------------------------------
async def build_app():
    research_agent, crm_agent = await build_agent_nodes()

    research_node = wrap_as_subgraph(research_agent, name="research_agent")
    crm_node = wrap_as_subgraph(crm_agent, name="crm_agent")

    def call_research(state: AgentState):
        # 用 .invoke 呼叫 subgraph 前，把外層 state 需要的欄位一起帶進去
        result = research_node.invoke(
            {
                "messages": state["messages"],
                "user_id": state["user_id"],
                "session_token": state["session_token"],
            }
        )
        # 只取最後一則回覆寫回外層,避免內部細節污染主線對話
        return {"messages": [result["messages"][-1]]}

    def call_crm(state: AgentState):
        result = crm_node.invoke(
            {
                "messages": state["messages"],
                "user_id": state["user_id"],
                "session_token": state["session_token"],
            }
        )
        return {"messages": [result["messages"][-1]]}

    outer = StateGraph(AgentState)
    outer.add_node("research", call_research)
    outer.add_node("crm", call_crm)
    outer.add_edge(START, "research")
    outer.add_edge("research", "crm")

    return outer.compile()


async def main():
    app = await build_app()
    result = await app.ainvoke(
        {
            "messages": [HumanMessage(content="幫我查一下 langgraph 的文件，再查一下客戶 A 的資料")],
            "user_id": "u-12345",
            "session_token": "sess-abcde",
        }
    )
    for m in result["messages"]:
        m.pretty_print()


if __name__ == "__main__":
    asyncio.run(main())
