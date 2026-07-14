import asyncio
import os
import pandas as pd
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain.tools import tool

load_dotenv()
MODEL_NAME = os.environ["MODEL_NAME"]
MODEL_URL = os.environ["MODEL_URL"]
API_KEY = os.environ["API_KEY"]


model = ChatOpenAI(
    model=MODEL_NAME, 
    temperature=0,
    base_url=MODEL_URL, 
    api_key=API_KEY
)


def _check_csv_exist(csv_path: str) -> bool:
    """檢查 CSV 檔案是否存在"""
    return


def _read_csv(csv_path: str) -> pd.DataFrame:
    """讀取 CSV 檔案"""
    return


def _check_db_exist(db_path: str) -> bool:
    """檢查 DB 資料庫是否存在"""
    return


def _create_db(db_path: str) -> bool:
    """新增一個 DB 資料庫"""
    return


DATA_AGENT_PROMPT = (
    "你是資料載入專家，負責處理用戶的資料，用於後續分析過程，"
    "你的職責是將用戶的 CSV 檔案寫入 DuckDB 的資料庫，"
    "避免後續分析時，修改用戶的原始檔案。"
)
data_agent = create_agent(
    model,
    tools=[],
    system_prompt=DATA_AGENT_PROMPT
)

    question = f"資料庫在 {DATABASE_PATH},幫我查一下 raw_data 這張表有哪些欄位。"
    result = await agent.ainvoke({"messages": [{"role": "user", "content": question}]})

    for message in result["messages"]:
        message.pretty_print()


if __name__ == "__main__":
    asyncio.run(main())
