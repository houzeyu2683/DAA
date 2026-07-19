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
from routers.orchestration import orchestration_router
import uuid
import asyncio


def build_workflow() -> CompiledStateGraph :
    """"""

    graph = StateGraph(OrchestrationState)
    graph.add_node("orchestration", orchestration_node)
    graph.add_node("data", data_node)
    graph.add_node("analysis", analysis_node)
    graph.add_node("chart", chart_node, retry=RetryPolicy(max_attempts=3))
    graph.add_node("summary", summary_node)

    graph.add_edge(START, "orchestration")
    graph.add_conditional_edges(
        "orchestration",
        orchestration_router,
        {
            "data": "data",
            "analysis": "analysis",
            "chart": "chart",
            "summary": "summary",
            "reply": END,
        },
    )
    graph.add_edge("data", "orchestration")
    graph.add_edge("analysis", "orchestration")
    graph.add_edge("chart", "orchestration")
    graph.add_edge("summary", END)

    checkpointer = InMemorySaver()
    workflow = graph.compile(checkpointer=checkpointer)
    return (workflow)


async def main() -> bool:
    """"""

    workflow = build_workflow()

    config = {
        "configurable": {
            "thread_id": "666",
            "workspace": '.data/G72602/workspace/' + uuid.uuid4().hex[:6]
        }
    }
    user_data_path = ".data/archive/data.csv"
    question = (
        # 第一種
        # f"幫我讀取 {user_data_path} 檔案，我要針對欄位 'minutes_played' 以及 '包含 'feat_' 的欄位"
        # f"進行差異分析，找出差異最大的前面五個結果並且畫成 box chart，給我一個報告"
        # 第二種
        # f"幫我讀取 {user_data_path} 檔案，我要針對欄位 'minutes_played' 以及 '包含 'feat_' 的欄位"
        # f"進行差異分析，找出差異最大的前面五個結果，給我一個報告"
        # 第三種
        # f"幫我讀取 {user_data_path} 檔案，我要針對欄位 'minutes_played' 以及 'feat_1' 的欄位畫成 box chart"
        # 第四種
        f"幫我讀取 {user_data_path} 檔案，我要欄位 'minutes_played' 去分別對 'feat_1'、'feat_4'、'feat_8'、'feat_6'以及'feat_17' 欄位畫成 box chart"


        # f"幫我讀取 {USER_DATA_PATH} 檔案，我要針對欄位 'minutes_played' 以及 '包含 'feat_' 的欄位進行差異分析"
        # f"幫我讀取 {USER_DATA_PATH} 檔案，我要針對欄位 'minutes_played' 以及 '包含 'feat_' 的欄位進行差異分析，並找出差異最大的前面 3 個。"

    )
    # question = (
    #     f"幫我讀取 {USER_DATA_PATH} 檔案，資料庫路徑是 {DATABASE_PATH}，"
    #     f"我要針對欄位 'team' 以及 'age' 的欄位進行 ANOVA 分析，然後畫箱型圖。"
    # )
    state = OrchestrationState(messages=[HumanMessage(question)], next=None)
    result = await workflow.ainvoke(
        state,
        config,
    )
    for message in result['messages']:
        message.pretty_print()
        continue
    
    return True


if __name__ == "__main__":
    asyncio.run(main())
    # print('done')