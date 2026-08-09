from typing import TypedDict, Literal

from langgraph.graph import MessagesState


class Task(TypedDict):
    direction: Literal["data", "analysis", "chart", "summary", "reply"]
    action: str


class State(MessagesState):
    tasks: list[Task]
    index: int
    error: bool
