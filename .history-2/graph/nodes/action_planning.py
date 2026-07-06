from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import add_messages
from typing import TypedDict, Annotated, List
from operator import add
from langgraph.types import interrupt
from graph.state import State

# from core import get_model

# _system_template = '''
# '''

# _model = get_model()

def action_planning(state: State, config: RunnableConfig) -> dict:
    
    #
    # _system_content = _system_template
    # conversation = [SystemMessage(_system_content)] + state["messages"]
    
    #
    # model = _model.with_structured_output
    # response = model.invoke(conversation)
    # message = response
    
    # 假設成功
    tasks = [
        "讀取 process_tracking 表中的 Equipment 與所有 CP_ 開頭的欄位",
        "執行 ANOVA 分析",
        "找出差異最大的三組 Equipment",
        "繪製 Box Chart",
        "輸出分析結果"
    ]

    response_content = '''
        [
            "讀取 process_tracking 表中的 Equipment 與所有 CP_ 開頭的欄位",
            "執行 ANOVA 分析",
            "找出差異最大的三組 Equipment",
            "繪製 Box Chart",
            "輸出分析結果"
        ]
    '''
    message = AIMessage(response_content)
    return {'messages': [message], tasks: tasks}
