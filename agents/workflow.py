import sys
import asyncio
import uuid

from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.tracers import ConsoleCallbackHandler

from agents.state import State
from agents.callbacks.tokens import TokenUsageCallbackHandler
from agents.callbacks.timing import TimingCallbackHandler
from agents.planning import planning
from agents.orchestration import orchestration
from agents.reply import reply
from agents.summarization import summarization
from agents.tables.data import data
from agents.tables.analysis import analysis
from agents.tables.chart import chart
from agents.tables.summary import summary

sys.stdout.reconfigure(encoding="utf-8")

diagram = StateGraph(State)

diagram.add_node("planning", planning)
diagram.add_node("orchestration", orchestration)
diagram.add_node("reply", reply)
diagram.add_node("data", data)
diagram.add_node("analysis", analysis)
diagram.add_node("chart", chart)
diagram.add_node("summary", summary)
diagram.add_node("summarization", summarization)

diagram.add_edge(START, "planning")
diagram.add_edge("planning", "orchestration")
diagram.add_edge("data", "orchestration")
diagram.add_edge("analysis", "orchestration")
diagram.add_edge("chart", "orchestration")
diagram.add_edge("summary", "orchestration")
diagram.add_edge("summarization", "orchestration")
diagram.add_edge("reply", END)

memory = MemorySaver()
graph = diagram.compile(checkpointer=memory)
 
class Workflow:

    def __init__(self, graph: CompiledStateGraph, debug: bool) -> None:
        self.graph = graph
        self.debug = debug
        return
    
    async def get_response(
        self,
        thread_id: str,
        session_workspace: str,
        database_path: str,
        table_names: list[str],
        user_message: str
    ) -> State:

        token_callback = TokenUsageCallbackHandler()
        timing_callback = TimingCallbackHandler()
        config = {
            "configurable": {
                "thread_id": thread_id,
                "session_workspace": session_workspace,
                "database_path": database_path,
                "table_names": table_names,
            },
            "callbacks": [token_callback, timing_callback]
        }

        if self.debug:
            process_callback = ConsoleCallbackHandler()
            config["callbacks"] += [process_callback]

        state = {
            "messages": [
                {"role": "user", "content": user_message}
            ]
        }
        response = await self.graph.ainvoke(state, config=config)
        token_information = (
            f"total_tokens: {token_callback.total_tokens} "
            f"(prompt: {token_callback.prompt_tokens}, "
            f"completion: {token_callback.completion_tokens})"
        )
        print(token_information)
        for record in timing_callback.records:
            print(record)
        return response

    async def stream(self, *args, **kwargs):
        ...


if __name__ == "__main__":

    
    workflow = Workflow(graph=graph, debug=True)

    user_message = (
        "這個資料集裡有多少筆資料? "
        "我想對 age 與 包含 passes 欄位進行相似度分析"
        "我想知道正相關對大與負相關最大的因子，"
        "幫我所有分析結果用水平圖畫出來，都畫在同一張圖。"
    )

    result = asyncio.run(workflow.get_response(
        thread_id=str(uuid.uuid4()),
        session_workspace=".data",
        database_path=".data/data.db",
        table_names=["fifa_world_cup_2026_player_performance"],
        user_message=user_message,
    ))

    for message in result["messages"]:
        message.pretty_print()
