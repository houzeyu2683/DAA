from langgraph.graph import MessagesState
from typing import TypedDict, Literal, Union

class Task(TypedDict):
    direction: Literal["overview", "chart", "report", "reply", "analysis"]
    action: str

class State(MessagesState):
    tasks: list[Task]
    index: int
    status: Literal['error', 'continue', 'done']
