import duckdb
import pandas as pd
import os
from os import makedirs
from uuid import uuid4
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

##
# from core.functions import getModel
from core import getModel
from core.status import State
# from nodes.initial import initial_node
from nodes.human import human_node
from nodes.intent import intent_node
from nodes.chat import chat_node
from nodes.clarify import clarify_node
# from nodes.plan import plan_node
# from nodes.sql import sql_node
# from nodes.pd import pd_node
from nodes.stats import stats_node
from nodes.plot import plot_node
from nodes.report import report_node
from routers.intent import intent_router
# from routers.execute import execute_router



##
if __name__ == '__main__':

    ##  用戶登入
    user_id = '6300727'
    ##  分配一個 thread 用來表示這次的談話
    thread_id = uuid4().hex[:4]
    ##  新增一個空間用來存放個人資料
    makedirs(f'./.data/.workspace/{user_id}/{thread_id}', exist_ok=True)

    """
    初始化狀態與設定
    """
    state = State(
        messages=[],
        intent="", 
        tables=[], 
        tasks=[],
        stats=[]
    )
    config = {
        'configurable': {
            'user_id': user_id,
            'thread_id': thread_id, 
            'workspace': f'./.data/workspace/{user_id}/{thread_id}',
            'database': database #f'./.data/workspace/{user_id}/{thread_id}/database.db',
        }
    }

    """
    組裝 Graph
    """
    builder = StateGraph(State)
    # builder.add_node("initial", initial_node)
    builder.add_node("human", human_node)
    builder.add_node("intent", intent_node)
    builder.add_node("chat", chat_node)
    builder.add_node("clarify", clarify_node)
    builder.add_node("stats", stats_node)
    builder.add_node("plot", plot_node)
    builder.add_node("report", report_node)
    
    builder.add_edge(START, "human")
    builder.add_edge('human', "intent")
    builder.add_conditional_edges("intent", intent_router, {
        "chat": "chat",
        "clarify": "clarify",
        "stats": "stats",
    })
    builder.add_edge('chat', "human")
    builder.add_edge('clarify', "human")
    builder.add_edge("stats", "plot")
    builder.add_edge("plot", "report")
    builder.add_edge("report", "human")
    
    # builder.add_edge("initial", "human")
    # builder.add_edge("human", "intent")
    # builder.add_edge("chat", "human")
    # builder.add_edge("clarify", "human")

    # task_mapping = {
    #     'sql': "sql",
    #     'pd': "pd",
    #     "stats": 'stats',
    #     'plot': 'plot',
    #     'report': 'report'
    # }
    # builder.add_conditional_edges(
    #     "plan", 
    #     execute_router,
    #     task_mapping
    # )
    # builder.add_conditional_edges('sql', execute_router, task_mapping)
    # builder.add_conditional_edges('pd', execute_router, task_mapping)
    # builder.add_conditional_edges('stats', execute_router, task_mapping)
    # builder.add_conditional_edges('plot', execute_router, task_mapping)
    # builder.add_edge('report', 'human')
 
    graph = builder.compile(checkpointer=MemorySaver())
    # import PIL.Image, io
    # picture = PIL.Image.open(io.BytesIO(graph.get_graph().draw_mermaid_png()))
    # picture.save("./picture.png")

    """
    執行
    """
    graph.invoke(state, config=config)
    while True:
        data_path = '.data/frame.csv'
        user_input = f"""
        讀取{data_path}，我要針對'Equipment'跟包含'_wat'的欄位進行 ANOVA 分析，
        將分析結果中差異最大的前五個找出來，畫出對應的 box-chart 圖，最後給我一個報告
        """
        if user_input == "EXIT":
            break
        result = graph.invoke(Command(resume=user_input), config=config)
        continue
