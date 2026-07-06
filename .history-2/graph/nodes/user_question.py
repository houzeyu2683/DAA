from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import add_messages
from typing import TypedDict, Annotated, List
from operator import add
from langgraph.types import interrupt
from graph.state import State

def user_question(state: State, config: RunnableConfig) -> dict:
    _, _ = state, config
    content = interrupt("用戶輸入")
    message = HumanMessage(content)
    return {"messages": [message]}