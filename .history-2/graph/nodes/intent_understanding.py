from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import add_messages
from typing import TypedDict, Annotated, List
from operator import add
from langgraph.types import interrupt
from graph.state import State

from core import get_model

# _system_template = '''
# 你是一個資料分析師，
# 但注意不要隨意幻想用戶沒有提出的需求。
# '''

# _model = get_model()

def intent_understanding(state: State, config: RunnableConfig) -> dict:
    
    #
    # _system_content = _system_template
    # conversation = [SystemMessage(_system_content)] + state["messages"]
    
    #
    # model = _model
    # response = model.invoke(conversation)
    # message = response
    
    # 假設成功
    response_content = """
        用戶要對表"process_tracking"中的欄位"Equipment"以及
        欄位包含"CP_"的資料做 anova 分析，接著將差異最大的三組"Equipment"找出來，
        把這三組的 box chart 畫出來。
    """
    message = AIMessage(response_content)

    return {'messages': [message]}
