from langgraph.graph import add_messages
from typing import TypedDict, Annotated, List, Dict
from operator import add


class State(TypedDict):
    messages: Annotated[List, add_messages]
    tasks: List
