from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, START, END

from nodes.coordination import coordination_node, CoordinationState
from nodes.data import data_node
from nodes.analysis import analysis_node
from nodes.chart import chart_node
from nodes.summary import summary_node
from routers.coordination import coordination_router


graph = StateGraph(CoordinationState)
graph.add_node("coordination", coordination_node)
graph.add_node("data", data_node)
graph.add_node("analysis", analysis_node)
graph.add_node("chart", chart_node)
graph.add_node("summary", summary_node)

graph.add_edge(START, "coordination")
graph.add_conditional_edges(
    "coordination",
    coordination_router,
    {
        "data": "data",
        "analysis": "analysis",
        "chart": "chart",
        "summary": "summary",
        "reply": END,
    },
)
graph.add_edge("data", "coordination")
graph.add_edge("analysis", "coordination")
graph.add_edge("chart", "coordination")
graph.add_edge("summary", END)

checkpointer = InMemorySaver()
workflow = graph.compile(checkpointer=checkpointer)


config = {
    "configurable": {
        "thread_id": "666",
        "workspace": '.data/G72602/workspace'
    }
}
USER_DATA_PATH = ".data/archive/fifa_world_cup_2026_player_performance.csv"
# DATABASE_PATH = ".data/tmp/data_agent_demo/database.db"

# question = (
#     f"幫我讀取 {CSV_PATH} 檔案，資料庫路徑是 {DB_PATH}，"
#     f"我要針對欄位 'minutes_played' 以及 'team' 的欄位進行 ANOVA 分析"
# )
# question = (
#     f"幫我讀取 {USER_DATA_PATH} 檔案，資料庫路徑是 {DATABASE_PATH}，"
#     f"我要針對欄位 'team' 以及 'age' 的欄位進行 ANOVA 分析，然後畫箱型圖。"
# )
question = (
    f"幫我讀取 {USER_DATA_PATH} 檔案，"
    f"我要針對欄位 'team' 以及 'age' 的欄位進行 ANOVA 分析，然後畫箱型圖。"
)

if __name__ == "__main__":
    result = workflow.invoke(
        {"messages": [{"role": "user", "content": question}]},
        config,
    )
    for message in result["messages"]:
        message.pretty_print()
