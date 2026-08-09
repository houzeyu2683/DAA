from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from agents.state import State
from agents.summarization import KEEP_RECENT_MESSAGE_COUNT


MESSAGE_COUNT_THRESHOLD = KEEP_RECENT_MESSAGE_COUNT * 2


def orchestration(state: State, config: RunnableConfig) -> Command:

    if state.get("error"):
        return Command(goto="reply")

    next_index = state["index"] + 1

    if next_index >= len(state["tasks"]):
        return Command(goto="reply")

    if len(state["messages"]) > MESSAGE_COUNT_THRESHOLD:
        return Command(goto="summarization")

    next_task = state["tasks"][next_index]
    return Command(goto=next_task["direction"], update={"index": next_index})
