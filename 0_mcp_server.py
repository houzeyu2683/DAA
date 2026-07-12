"""
Notebook 0: 最小可行的 MCP server。

目的:先搞懂「定義一個工具」跟「跑起一個 MCP server」這兩件事,
還不牽扯 DuckDB / LangGraph。工具的 type hint + docstring 會被
FastMCP 自動轉成 schema,這份 schema 之後就是 LLM 判斷要不要呼叫
這個工具的依據。
"""

import duckdb
import numpy as np
import pandas as pd
from mcp.server.fastmcp import FastMCP

DB_PATH = "notebooks/toy.db"

mcp = FastMCP(name="basics-server", host="127.0.0.1", port=8000)


@mcp.tool()
def echo(text: str) -> str:
    """把傳入的文字原封不動送回去,用來確認串接有沒有通。"""
    return text


@mcp.tool()
def add(a: int, b: int) -> int:
    """回傳 a + b。"""
    return a + b


@mcp.tool()
def sum_list(numbers: list[int]) -> int:
    """回傳一組整數的總和。"""
    return sum(numbers)


@mcp.tool()
def describe_lineage(name: str, parent_tables: list[str]) -> str:
    """模擬之後 register 工具會用到的血緣描述:某個 artifact 是由哪些既有表衍生出來的。"""
    if not parent_tables:
        return f"{name} 沒有 parent_tables,是原始載入的表。"
    parents = ", ".join(parent_tables)
    return f"{name} 衍生自: {parents}"


def _read_schema(path: str) -> list[str]:
    """純內部邏輯,不是 MCP 工具,LLM 看不到它,只是給其他工具重用。"""
    return list(pd.read_csv(path, nrows=5).columns)


@mcp.tool()
def get_schema(path: str) -> list[str]:
    """查看某份 CSV 檔案有哪些欄位。"""
    return _read_schema(path)


@mcp.tool()
def load_csv(path: str) -> str:
    """讀取一份 CSV,建成 DuckDB 裡的一張表。
    表名固定叫 raw_<檔名去掉副檔名>。"""
    schema = _read_schema(path)

    table_name = "raw_" + path.split("/")[-1].split("\\")[-1].rsplit(".", 1)[0]

    df = pd.read_csv(path)
    con = duckdb.connect(DB_PATH)
    try:
        con.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM df")
    finally:
        con.close()

    return f"已建表 {table_name},共 {len(df)} 筆,欄位:{schema}"


@mcp.tool()
def run_sql(query: str) -> list[dict]:
    """對玩具資料庫執行一句唯讀 SELECT 查詢,回傳結果列(每列是一個 dict)。"""
    if not query.strip().lower().startswith("select"):
        raise ValueError("只允許 SELECT 查詢。")
    con = duckdb.connect(DB_PATH, read_only=True)
    try:
        return con.execute(query).fetchdf().to_dict(orient="records")
    finally:
        con.close()


@mcp.tool()
def run_python(code: str) -> str:
    """執行一段 Python 程式碼。程式碼裡可以直接用變數 df 存取
    sensor_readings 表的完整內容(pandas DataFrame),也可以用 pd/np。
    程式碼的最後一行必須是一個運算式,它的值會被當作回傳結果。"""
    con = duckdb.connect(DB_PATH, read_only=True)
    try:
        df = con.execute("SELECT * FROM sensor_readings").fetchdf()
    finally:
        con.close()

    scope = {"df": df, "pd": pd, "np": np}
    lines = code.strip().splitlines()
    *body, last = lines
    if body:
        exec("\n".join(body), scope)
    return repr(eval(last, scope))


if __name__ == "__main__":
    mcp.run(transport="streamable-http")

# INFO:     Started server process [9744]
# INFO:     Waiting for application startup.
# StreamableHTTP session manager started
# INFO:     Application startup complete.
# INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
# Created new transport with session ID: e903f7b044f349169a01d6f2792ee7b3
# INFO:     127.0.0.1:63334 - "POST /mcp HTTP/1.1" 200 OK
# INFO:     127.0.0.1:63335 - "POST /mcp HTTP/1.1" 202 Accepted
# INFO:     127.0.0.1:63336 - "GET /mcp HTTP/1.1" 200 OK