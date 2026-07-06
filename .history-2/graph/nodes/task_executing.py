from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import add_messages
from typing import TypedDict, Annotated, List
from operator import add
from langgraph.types import interrupt

from graph.state import State
from core import get_model
from tools import selesct

_model = get_model()

_system_template = '''
你是一個資料分析師，你將善用你手上的工具去完成任務。
'''

def task_executing(state: State, config: RunnableConfig) -> dict:

    model_with_tools = _model.bind_tools(tools)
    
    system_content = _system_template
    human_content = state["tasks"][0]
    
    conversation = [
        SystemMessage(system_content), 
        HumanMessage(human_content)
    ]
    
    #
    # model = _model.with_structured_output
    response = model_with_tools.invoke(conversation)
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
