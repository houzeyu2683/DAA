"""
用自己搭建的 LangGraph StateGraph（不透過 langchain.agents.create_agent）
示範同時擁有：真正逐 token 串流 + tool-calling + thread_id 記憶。

背景：langchain.agents.create_agent() 內部呼叫模型時用 model.ainvoke(messages)，
完全沒有轉傳 config，導致 stream_mode="messages" 永遠只能拿到一整包完整訊息，
沒辦法逐字串流。這裡示範只要在自訂 node 裡把 config 轉傳給 model.ainvoke()，
LangGraph 就會自動偵測到串流用的 callback handler，逐 token 把內容吐出來。

執行方式：
    conda run -n DAA python exp-try/streaming_tool_graph.py
"""

import asyncio
import os
import sys
from pathlib import Path

import dotenv
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

sys.path.append(str(Path(__file__).resolve().parent.parent))

from agenticend.tools.system import is_file_exist

dotenv.load_dotenv()

model = ChatOpenAI(
    model=os.environ["MODEL_NAME"],
    base_url=os.environ["MODEL_URL"],
    api_key=os.environ["MODEL_KEY"],
    temperature=0,
)

tools = [is_file_exist]
model_with_tools = model.bind_tools(tools)


async def call_model(state: MessagesState, config) -> dict:
    # 關鍵在這裡：把 config 轉傳給 ainvoke，stream_mode="messages" 才會逐 token 送出。
    response = await model_with_tools.ainvoke(state["messages"], config)
    return {"messages": [response]}


builder = StateGraph(MessagesState)
builder.add_node("model", call_model)
builder.add_node("tools", ToolNode(tools))
builder.add_edge(START, "model")
# tools_condition 會檢查最新一則 AIMessage 有沒有 tool_calls，
# 有就跳到 "tools" node，沒有就結束（等同框架內建的 tool 迴圈判斷）。
builder.add_conditional_edges("model", tools_condition)
builder.add_edge("tools", "model")

graph = builder.compile(checkpointer=InMemorySaver())


async def ask(config: dict, question: str) -> None:
    print(f"\n> {question}")
    last_message_id = None
    async for chunk, _ in graph.astream(
        {"messages": [HumanMessage(content=question)]},
        config=config,
        stream_mode="messages",
    ):
        # 一般文字回覆會逐 token 出現；ToolMessage（工具執行結果）本身
        # 不是模型生成的 token，所以會是一整包出現，這是正常現象。
        if chunk.content:
            if last_message_id is not None and chunk.id != last_message_id:
                print()
            print(chunk.content, end="", flush=True)
            last_message_id = chunk.id
    print()


async def main() -> None:
    config = {"configurable": {"thread_id": "exp-try-demo"}}

    print("=== 第一輪：一般問答，不會觸發 tool ===")
    await ask(config, "請用一句話自我介紹")

    print("\n=== 第二輪：會觸發 tool_call 的問題 ===")
    await ask(config, "幫我檢查 /etc/hosts 這個檔案存不存在")

    print("\n=== 第三輪：驗證同一個 thread_id 記得前面的對話 ===")
    await ask(config, "我剛剛問你檢查的是哪個檔案？")


if __name__ == "__main__":
    asyncio.run(main())
