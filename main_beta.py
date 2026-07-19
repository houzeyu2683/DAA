import asyncio
import uuid
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.types import RetryPolicy
from langgraph.graph.state import CompiledStateGraph
from langchain_core.messages import HumanMessage
from nodes.orchestration import orchestration_node, OrchestrationState
from nodes.data import data_node
from nodes.analysis import analysis_node
from nodes.chart import chart_node
from nodes.summary import summary_node
from nodes.system import system_node
from routers.orchestration import orchestration_router
import uuid
import asyncio

from langchain_core.messages import HumanMessage

from nodes.orchestration import OrchestrationState


def build_workflow() -> CompiledStateGraph :
    """"""

    graph = StateGraph(OrchestrationState)
    graph.add_node("orchestration", orchestration_node)
    graph.add_node("data", data_node)
    graph.add_node("analysis", analysis_node)
    graph.add_node("chart", chart_node, retry=RetryPolicy(max_attempts=3))
    graph.add_node("summary", summary_node)
    graph.add_node("system", system_node)

    graph.add_edge(START, "orchestration")
    graph.add_conditional_edges(
        "orchestration",
        orchestration_router,
        {
            "data": "data",
            "analysis": "analysis",
            "chart": "chart",
            "summary": "summary",
            "system": "system",
            "reply": END,
        },
    )
    graph.add_edge("data", "orchestration")
    graph.add_edge("analysis", "orchestration")
    graph.add_edge("chart", "orchestration")
    graph.add_edge("system", "orchestration")
    graph.add_edge("summary", END)

    checkpointer = InMemorySaver()
    workflow = graph.compile(checkpointer=checkpointer)
    return (workflow)


async def main() -> bool:
    """讓使用者在終端機裡連續提問，同一個 thread_id 讓對話歷史被 checkpointer 保留下來。"""

    workflow = build_workflow()

    config = {
        "configurable": {
            "thread_id": "666",
            "workspace": '.data/G72602/workspace/' + uuid.uuid4().hex[:6],
        }
    }

    print("輸入問題開始對話，輸入 exit 離開。")

    while True:
        question = input("\n你：").strip()
        if question.lower() in ("exit", "quit"):
            break
        if not question:
            continue

        state = OrchestrationState(messages=[HumanMessage(question)], next=None)
        result = await workflow.ainvoke(state, config)

        for message in result["messages"]:
            message.pretty_print()

    return True


if __name__ == "__main__":
    asyncio.run(main())
