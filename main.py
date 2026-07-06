from os import makedirs
from uuid import uuid4

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from core.state import State
from graph.nodes import (
    user_question, 
    action_planning, 
    intent_understanding,
    data_processing, 
    stats_processing, 
    chart_processing, 
    report_processing,
    routers
)
import asyncio

def main():
    ##  用戶登入
    user_id = uuid4().hex[:4]
    ##  分配一個 thread 用來表示這次的談話
    thread_id = uuid4().hex[:4]
    ##  新增一個空間用來存放個人資料
    workspace = f'./.data/workspace/{user_id}/{thread_id}'
    makedirs(workspace, exist_ok=True)

    """
    初始化狀態與設定
    """
    state = State(messages=[], intent="", tasks=[], tables=[], charts=[], history=[])
    config = {
        'configurable': {
            'user_id': user_id,
            'thread_id': thread_id,
            'workspace': workspace,
            'database': 'data.db'
        }
    }

    """
    組裝 Graph
    目前只接到 action_planning，先驗證規劃出來的 tasks 品質，
    data_processing / stats_processing / chart_processing / result_summary 之後再接上去。
    """
    builder = StateGraph(State)
    builder.add_node("user_question", user_question)
    builder.add_node("intent_understanding", intent_understanding)
    builder.add_node("action_planning", action_planning)
    #
    builder.add_node("data_processing", data_processing)
    builder.add_node("stats_processing", stats_processing)
    builder.add_node("chart_processing", chart_processing)
    builder.add_node("report_processing", report_processing)
    #
    builder.add_edge(START, "user_question")
    builder.add_edge("user_question", "intent_understanding")
    builder.add_edge("intent_understanding", "action_planning")
    builder.add_edge("action_planning", 'data_processing')
    builder.add_conditional_edges(
        "data_processing", routers.task_executing, {
            "STATS": "stats_processing",
            "CHART": "chart_processing",
        }
    )
    builder.add_conditional_edges(
        "stats_processing", routers.task_executing, {
            "CHART": "chart_processing",
            "REPORT": "report_processing"
        }
    )
    builder.add_edge("chart_processing", "report_processing")
    builder.add_edge("report_processing", END)
    graph = builder.compile(checkpointer=MemorySaver())
    graph.get_graph().draw_png('graph.png')

    """
    執行
    """
    # user_input = """
    # 讀取 '.data/frame.csv' 表，我要針對 Equipment 跟包含 _wat 的欄位進行 ANOVA 分析，
    # 將分析結果中差異最大的前五個找出來，最後給我一個報告
    # """
    user_input = """
    讀取 '.data/frame.csv' 表，我要針對 Equipment 跟包含 _wat 的欄位進行 ANOVA 分析，
    將分析結果中差異最大的前五個找出來，畫出對應的 box-chart 圖，最後給我一個報告
    """
    # user_input = """
    # 讀取 '.data/frame.csv' 表，我要針對 Equipment 跟包含 wat_12 的欄位畫出對應的 scatter 圖
    # """
    state["messages"] = [user_input]
    result = graph.invoke(state, config=config)

    print("intent:", result["intent"])
    for task in result["tasks"]:
        print(task)

##
if __name__ == '__main__':
    # asyncio.run(main())
    main()