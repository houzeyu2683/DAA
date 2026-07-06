from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from core.state import State


def chart_processing(state: State, config: RunnableConfig) -> dict:
    """依統計結果繪製圖表（如 box chart）並存檔。"""
    # TODO: implement
    return {}
