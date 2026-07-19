import os
from typing import Optional
import uuid
import duckdb as db
import pandas as pd
from dotenv import load_dotenv
from scipy import stats
from langchain_core.messages import SystemMessage, HumanMessage
from langchain.agents import create_agent
from langgraph.graph import END
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableConfig

from nodes.orchestration import OrchestrationState

load_dotenv()
MODEL_NAME = os.environ["model_name"]
MODEL_URL = os.environ["base_url"]
API_KEY = os.environ["api_key"]

model = ChatOpenAI(
    model=MODEL_NAME,
    temperature=0,
    base_url=MODEL_URL,
    api_key=API_KEY,
)

SUMMARY_SYSTEM_PROMPT = (
    "你是資料分析解讀專家，負責在整個資料分析流程結束前，回覆使用者最原始的問題。\n"
    "優先順序如下：\n"
    "1. 最重要的是直接回答使用者一開始問的問題本身。"
    "如果對話紀錄裡已經有統計分析的實際數字(例如 p_value、f_stat)，"
    "必須用白話文講出結論(例如兩組之間是否有顯著差異)，"
    "不能只回報「已完成分析」這種流程性的話卻不講結論。"
    "結論一律以工具實際回傳的數字為準，不能自己編數字。\n"
    "2. 其次才是補充關鍵資訊(例如資料庫路徑、表名、統計結果表名、圖檔路徑)。\n"
    "3. 不要反問使用者沒有要求過的下一步(例如使用者沒問畫圖，就不要主動問要不要畫圖)。\n"
    "禁止產生任何程式碼。"
)
summary_agent = create_agent(model)

# def _ensure_system_prompt(messages: list, prompt: str) -> list:
#     if messages and getattr(messages[0], "type", None) == "system":
#         return messages
#     return [{"role": "system", "content": prompt}] + list(messages)


def summary_node(state: OrchestrationState) -> dict:
    """整合對話紀錄，產生最終總結訊息。"""
    messages = [SystemMessage(SUMMARY_SYSTEM_PROMPT)] + state["messages"]
    # messages = _ensure_system_prompt(state["messages"], SUMMARY_PROMPT)
    response = summary_agent.invoke({"messages": messages})

    for message in response['messages']:
        message.pretty_print()


    update = {"messages": response["messages"][-1:]}
    return update
