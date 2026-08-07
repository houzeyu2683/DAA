from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from .state import State


def compacting(state: State, config: RunnableConfig) -> Command:
    pass
