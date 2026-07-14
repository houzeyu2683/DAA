import asyncio
import os
import re
from collections import Counter
from pathlib import Path
import duckdb
import pandas as pd
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langgraph.checkpoint.memory import InMemorySaver


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
checkpointer = InMemorySaver()

def _check_csv_exist(csv_path: str) -> bool:
    """檢查 CSV 檔案是否存在"""
    return os.path.isfile(csv_path)


def _check_db_exist(db_path: str) -> bool:
    """檢查 DB 資料庫是否存在"""
    return os.path.isfile(db_path)


def _create_db(db_path: str) -> bool:
    """新增一個 DB 資料庫"""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(db_path)
    con.close()
    return _check_db_exist(db_path)


def _insert_tb(csv_path: str, db_path: str) -> dict:
    """將 CSV 檔案寫入指定的 DB 資料庫"""
    # if not _check_csv_exist(csv_path):
    #     return False

    # if not _check_db_exist(db_path):
    #     _create_db(db_path)

    tb_name = re.sub(r"[^a-zA-Z0-9_]", "_", Path(csv_path).stem)
    con = duckdb.connect(db_path)
    try:
        con.execute(
            f"CREATE OR REPLACE TABLE {tb_name} "
            f"AS SELECT * FROM read_csv_auto(?)",
            [csv_path]
        )
        row_count = con.execute(f"SELECT COUNT(*) FROM {tb_name}").fetchone()[0]
    finally:
        con.close()

    return {"tb_name": tb_name, "row_count": row_count}


def _describe_tb(db_path: str, tb_name: str) -> dict:
    """概述資料庫中的表"""

    con = duckdb.connect(db_path, read_only=True)
    try:
        df = con.execute(f"SELECT * FROM {tb_name} LIMIT 20").df()
        col_count = len(df.columns)
        row_count = con.execute(
            f"SELECT COUNT(*) FROM {tb_name}"
        ).fetchone()[0]
    finally:
        con.close()

    dtype_counts = dict(Counter(df.dtypes.astype(str)))
    tb_preview = df.to_string(
        max_cols=12, max_rows=12, show_dimensions=False
    )
    return {
        "tb_name": tb_name,
        "row_count": row_count,
        "col_count": col_count,
        "dtype_counts": dtype_counts,
        "tb_preview": tb_preview,
    }


@tool
def check_csv_exist(csv_path: str) -> bool:
    """檢查指定路徑的 CSV 檔案是否存在。

    參數:
        csv_path: CSV 檔案的路徑。
    """
    return _check_csv_exist(csv_path)


@tool
def check_db_exist(db_path: str) -> bool:
    """檢查指定路徑的 DuckDB 資料庫是否存在。

    參數:
        db_path: DuckDB 資料庫檔案的路徑。
    """
    return _check_db_exist(db_path)


@tool
def create_db(db_path: str) -> bool:
    """在指定路徑新增一個空的 DuckDB 資料庫。

    參數:
        db_path: 要建立的 DuckDB 資料庫檔案路徑。
    """
    return _create_db(db_path)


@tool
def insert_tb(csv_path: str, db_path: str) -> dict:
    """讀取一份 CSV 檔案，寫入指定的 DuckDB 資料庫，成為一張新的表。

    表名會根據 CSV 檔名自動產生(轉成合法的 SQL 識別字)。

    參數:
        csv_path: CSV 檔案的路徑。
        db_path: 要寫入的 DuckDB 資料庫檔案路徑。
    """
    return _insert_tb(csv_path, db_path)


@tool
def describe_tb(db_path: str, tb_name: str) -> dict:
    """查詢指定資料表的概況,包含筆數、欄位數、各型別欄位數量統計,以及部分資料預覽。

    參數:
        db_path: DuckDB 資料庫檔案的路徑。
        tb_name: 要查詢的資料表名稱。
    """
    return _describe_tb(db_path, tb_name)


tools = [check_csv_exist, check_db_exist, create_db, insert_tb, describe_tb]
DATA_AGENT_PROMPT = (
    "你是資料載入專家，負責處理用戶的資料，用於後續分析過程，"
    "你的職責是將用戶的 CSV 檔案寫入 DuckDB 的資料庫，"
    "避免後續分析時，修改用戶的原始檔案。"
)
data_agent = create_agent(
    model,
    tools=tools,
    system_prompt=DATA_AGENT_PROMPT,
    checkpointer=checkpointer
)


config = {"configurable": {"thread_id": "666"}}
CSV_PATH = ".data/archive/data_trans.csv"
DB_PATH = ".data/tmp/data_agent_demo/database.db"

question = (
    f"CSV 檔案路徑是 {CSV_PATH},"
    f"DuckDB 資料庫路徑是 {DB_PATH}。"
    f"幫我把這份 CSV 寫入資料庫，然後告訴我這個表有幾筆資料、有多少欄位。"
)


if __name__ == "__main__":
    result = data_agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
        config,
    )
    for message in result["messages"]:
        message.pretty_print()


