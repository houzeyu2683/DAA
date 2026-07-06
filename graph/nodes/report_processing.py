from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from core.state import State


def report_processing(state: State, config: RunnableConfig) -> dict:
    """彙整分析與圖表結果，產出最終報告給用戶。"""
    # TODO: implement
    return {}
