from langchain_core.messages import HumanMessage
from langgraph.types import interrupt

from core.status import State


def human_node(state: State) -> dict:
    content = interrupt("等待用戶輸入")
    return {"messages": [HumanMessage(content=content)]}
