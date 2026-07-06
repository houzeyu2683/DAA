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
# model = getModel()

##
if __name__ == '__main__':

    ##  用戶登入
    user_id = 'G72602' #uuid4().hex[:4]
    ##  分配一個 thread 用來表示這次的談話
    thread_id = uuid4().hex[:4]
    ##  新增一個空間用來存放本次對話的資料
    workspace = f'./.data/workspace/{user_id}/{thread_id}'
    makedirs(workspace, exist_ok=True)

    """
    狀態與設定
    當交互界面啟動的時候，用戶就可以開始聊天或上傳資料表格，
    所以即使用戶在前端上傳好資料表格，這個 session 也不會知道。
    因此 config 要放用戶的 workspace 就好。
    接著 state 可以在交互過程中去檢查 workspace 有沒有 database 被建立，
    如果檢查到有被建立，那就代表用戶上傳的資料表格。
    """
    state = State(messages=[], tables=[], intent="", tasks=[])
    config = {
        'configurable': {
            'user_id': user_id,
            'thread_id': thread_id, 
            'workspace': f'./.data/workspace/{user_id}/{thread_id}'
        }
    }

    """
    假設用戶完成上傳資料表格，後台已經將用戶上傳的表格輸入到特定的用戶資料庫
    """
    database = './.data/workspace.db'
    table_name = 'my_table'


    '''
    目前用戶上傳資料表格，要開始主要的下需求分析資料的情境
    '''
    builder = StateGraph(State)
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
        # user_input = input("User: ")
        # user_input = '幫我挑出欄位 Equipment 以及欄位 CP_50, CP_51, CP_52 的資料，接著執行 annova 分析，找出差異最大的三個機器，接著幫我把撈出來的資料畫 box chart ，我想知道機器以及CP之間的分佈'
        # user_input = "幫我查詢 Equipment 和 CP_50 的資料，對 Equipment 做 ANOVA 分析，看各機器的 CP_50 是否有顯著差異"
        # user_input = '我要查詢欄位"Equipment"以及欄位包含"CP_"的資料做 anova 分析'
        user_input = '我要欄位 Equipment 以及欄位 包含 CP_ 的資料做 anova 分析，並將差異最大的前五個用 box chart 來呈現'
        # user_input = '我要用欄位 Equipment 以及欄位 包含 CP_1 的資料畫 box chart ， Equipment要分組'
        if user_input == "EXIT":
            break
        result = graph.invoke(Command(resume=user_input), config=config)
        # for msg in result['messages']:
        #     if hasattr(msg, 'content') and msg.content:
        #         print(f"\n[{type(msg).__name__}] {msg.content}")
        # break
