import duckdb
import pandas as pd
import os
from langchain_openai import ChatOpenAI
from langgraph.graph import add_messages
from dotenv import load_dotenv
from os import getenv, makedirs
from uuid import uuid4
from langchain_core.messages import (
    SystemMessage, 
    AIMessage, 
    HumanMessage, 
    ToolMessage
)
from typing import TypedDict, Annotated
from operator import add

class StatsResult(TypedDict):
    method: str # "anova", "t-test" 等
    summary: str # 文字說明，給 LLM 看
    data: dict # 數字結果，給程式用


class Task(TypedDict):
    type: str
    description: str

class Table(TypedDict):
    name: str
    description: str

class State(TypedDict):
    messages: Annotated[list, add_messages]
    tables: Annotated[list[Table], add]
    intent: str
    tasks: list[Task]
    stats: Annotated[list[StatsResult], add]


# 對，你整個專案用不到 tool。

# 原因是你的流程是固定的線性步驟：

# 每一步要做什麼，你已經知道了
# LLM 只需要解析參數，不需要自主決策
# Tool 適合的場景是：LLM 自己不知道下一步要做什麼，需要動態探索。例如一個 agent 被丟進一個未知環境，自己決定要查什麼資料、呼叫什麼功能。

# 你的架構是 plan → 固定執行，這種情況 structured output 比 tool 更穩定、更可控。