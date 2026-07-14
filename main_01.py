import asyncio
import os
import re
import uuid
from collections import Counter
from pathlib import Path
from typing import Literal
import duckdb
import pandas as pd
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from scipy import stats as scipy_stats
from langchain.agents.middleware import HumanInTheLoopMiddleware 
from langgraph.checkpoint.memory import InMemorySaver 
from tools import data

_ = load_dotenv()
MODEL_URL = os.environ["MODEL_URL"]
API_KEY = os.environ["API_KEY"]
MODEL_NAME = os.environ["MODEL_NAME"]


model = ChatOpenAI(
    model=MODEL_NAME,
    temperature=0,
    api_key=API_KEY,
    base_url=MODEL_URL,
)


DATA_AGENT_PROMPT = (
    "你是資料操作專家,負責讀取 CSV、查看資料表的欄位結構。\n"
    "收到需要分析的表格路徑時,先用 load_table 建表,"
    "如果不確定欄位長什麼樣,再用 get_schema 確認。\n"
    "完成後,在回覆裡明確講出實際的表名跟關鍵欄位,"
    "因為委派你的上層 agent 需要這些具體資訊才能繼續下一步。"
)
def build_data_agent(database_path: str):
    database_prompt = (
        f"這次對話已經分配了一個專屬的工作空間,"
        f"裡面的 DuckDB 資料庫路徑是:{database_path}。\n"
        "凡是工具需要 database_path 這個參數時,一律使用這個路徑,"
        "不要自己猜測或編造其他路徑。"
    )
    return create_agent(
        model,
        tools=[data.load_table, data.get_schema],
        system_prompt=DATA_AGENT_PROMPT + database_prompt,
    )
def build_run_data_operations(database_path: str):
    @tool
    def run_data_operations(request: str) -> str:
        """當使用者需要讀取 CSV、查看資料表欄位時,呼叫這個工具..."""
        data_agent = build_data_agent(database_path)
        result = data_agent.invoke({"messages": [{"role": "user", "content": request}]})
        return result["messages"][-1].content
    return run_data_operations

# stats_agent = create_agent(
#     model,
#     tools=[],
#     system_prompt=STATS_AGENT_PROMPT
# )

# chart_agent = create_agent(
#     model,
#     tools=[],
#     system_prompt=CHART_AGENT_PROMPT
# )

SUPERVISOR_AGENT_PROMPT = (
    "你是一個資料分析助理的協調者(supervisor)。"
    "你自己不會讀資料、不會做統計、不會畫圖,"
    "所有實際工作都要委派給對應的專家:\n"
    "- 資料操作(讀取 CSV、查看表格欄位)→ 委派給資料專家\n"
    "- 統計分析(ANOVA、相關係數等)→ 委派給統計專家\n"
    "- 畫圖(box chart 等視覺化)→ 委派給圖表專家\n\n"
    "重要原則:\n"
    "1. 每個專家只看得到你這次傳給它的請求文字,看不到其他對話歷史,"
    "委派時務必把必要的具體資訊(表名、確切的欄位名稱)寫清楚,"
    "不要用「那些欄位」「剛才的結果」這種模糊指代。\n"
    "2. 任務之間如果有先後依賴(例如要先讀取資料才知道表名、"
    "要先看到統計結果才知道哪些欄位差異最大),"
    "就先完成前一步、從結果中取出具體資訊,再進行下一步委派——"
    "不要在還不知道答案時就先猜測欄位名稱。\n"
    "3. 全部委派完成後,把各專家的結果整合成一段清楚的摘要回答使用者。"
)

def build_supervisor_agent(database_path: str):
    run_data_operations = build_run_data_operations(database_path)
    return create_agent(
        model,
        tools=[run_data_operations],
        system_prompt=SUPERVISOR_AGENT_PROMPT,
        checkpointer=InMemorySaver(),
    )

if __name__=='__main__':
    user_question = (
        '幫我讀取".data/archive/data_trans.csv"，'
        '我想要對欄位"tournament_rating"以及包含"match_id"的欄位'
        '進行ANOVA分析，幫我把差異最大的前六個結果找出來，'
        '我想要對他們畫 box chart 圖。'
    )

    config = {
        "configurable": {
            "thread_id": "666"
        }
    }
    workspace = ".data/tmp/123" # 假設分配一個 workspace 給 user
    database_path = str(Path(workspace) / 'database.db')
    supervisor_agent = build_supervisor_agent(database_path)

    interrupts = []
    stream = supervisor_agent.stream_events(
        {"messages": [{"role": "user", "content": user_question}]},
        config,
        version='v3'
    )


    for kind, item in stream.interleave("messages", "tool_calls"):
        if kind == "messages":
            for token in item.text:
                print(token, end="", flush=True)
        elif kind == "tool_calls":
            print(f"\nTool call: {item.tool_name}({item.input})")

    