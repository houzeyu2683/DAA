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



@tool
def check_file_exist(file_path: str) -> bool:
    """檢查指定路徑的檔案是否存在。

    參數:
        file_path: 檔案的路徑。
    """
    return os.path.isfile(file_path)


@tool
def check_database_exist(database_path: str) -> bool:
    """檢查指定路徑的 DuckDB 資料庫是否存在。

    參數:
        database_path: DuckDB 資料庫檔案的路徑。
    """
    return os.path.isfile(database_path)


@tool
def check_table_exist(database_path: str, table_name: str) -> bool:
    """檢查指定的資料表是否存在於 DuckDB 資料庫中。

    參數:
        database_path: DuckDB 資料庫檔案的路徑。
        table_name: 要檢查的資料表名稱。
    """
    con = duckdb.connect(database_path, read_only=True)
    try:
        count = con.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
            [table_name]
        ).fetchone()[0]
    finally:
        con.close()
    return count > 0

@tool
def create_database(database_path: str) -> bool:
    """在指定路徑新增一個空的 DuckDB 資料庫，若上層資料夾不存在會一併建立。

    參數:
        database_path: 要建立的 DuckDB 資料庫檔案路徑。
    """
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(database_path)
    con.close()
    return True


@tool
def create_table(database_path: str, table_name: str, table_content: pd.DataFrame) -> bool:
    """在指定的 DuckDB 資料庫中新增一張資料表，並把資料寫入。
    若同名資料表已存在會被覆蓋。

    參數:
        database_path: DuckDB 資料庫檔案的路徑。
        table_name: 要建立的資料表名稱。
        table_content: 要寫入資料表的內容，型別為 pandas DataFrame。
    """
    con = duckdb.connect(database_path)
    try:
        con.register("table_content_view", table_content)
        con.execute(
            f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM table_content_view"
        )
    finally:
        con.close()
    return check_table_exist.invoke({"database_path": database_path, "table_name": table_name})


@tool
def list_tables(database_path: str) -> list:
    """列出指定 DuckDB 資料庫中所有的資料表名稱。

    參數:
        database_path: DuckDB 資料庫檔案的路徑。
    """
    con = duckdb.connect(database_path, read_only=True)
    try:
        tables = [row[0] for row in con.execute("SHOW TABLES").fetchall()]
    finally:
        con.close()
    return tables

@tool
def get_table_shape(database_path: str, table_name: str) -> list:
    """獲得資料表的資料數與欄位數，回傳 [row_count, col_count]。

    參數:
        database_path: DuckDB 資料庫檔案的路徑。
        table_name: 要查詢的資料表名稱。
    """
    con = duckdb.connect(database_path, read_only=True)
    try:
        row_count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        col_count = len(con.execute(f"DESCRIBE {table_name}").fetchall())
    finally:
        con.close()
    return [row_count, col_count]

@tool
def get_columns_type(database_path: str, table_name: str, columns_name: list) -> dict:
    """查詢資料表中指定欄位的型別。

    輸出格式範例: {"col_1": "BIGINT", "col_2": "VARCHAR", ....}

    參數:
        database_path: DuckDB 資料庫檔案的路徑。
        table_name: 要查詢的資料表名稱。
        columns_name: 要查詢型別的欄位名稱清單。
    """
    con = duckdb.connect(database_path, read_only=True)
    try:
        schema = con.execute(f"DESCRIBE {table_name}").fetchall()
    finally:
        con.close()
    types_by_col = {row[0]: row[1] for row in schema}
    return {col: types_by_col[col] for col in columns_name if col in types_by_col}

@tool
def get_columns_type_distribution(database_path: str, table_name: str, columns_pattern: dict) -> dict:
    """依欄位名稱比對規則，統計符合條件的欄位中各種型別各有幾個。

    columns_pattern 格式是 {pattern字串: 比對方式}，例如:
        - {"XXXX": "contains"}   欄位名稱包含 "XXXX"
        - {"XXXX": "startwith"}  欄位名稱開頭是 "XXXX"
        - {"XXXX": "endwith"}    欄位名稱結尾是 "XXXX"

    輸出格式範例: {"BIGINT": 22, "VARCHAR": 123, ....}

    參數:
        database_path: DuckDB 資料庫檔案的路徑。
        table_name: 要查詢的資料表名稱。
        columns_pattern: 欄位名稱的比對規則。
    """
    con = duckdb.connect(database_path, read_only=True)
    try:
        schema = con.execute(f"DESCRIBE {table_name}").fetchall()
    finally:
        con.close()

    matched_types = []
    for row in schema:
        col_name, col_type = row[0], row[1]
        for pattern, mode in columns_pattern.items():
            if mode == "contains" and pattern in col_name:
                matched_types.append(col_type)
                break
            if mode == "startwith" and col_name.startswith(pattern):
                matched_types.append(col_type)
                break
            if mode == "endwith" and col_name.endswith(pattern):
                matched_types.append(col_type)
                break

    return dict(Counter(matched_types))

@tool
def list_columns(database_path: str, table_name: str) -> str:
    """列出資料表的所有欄位名稱，串成一個字串。

    若欄位數量小於等於 12 個，直接用逗號串接全部欄位；
    若超過 12 個，只顯示前 3 個與後 3 個欄位名稱，中間用 '......' 省略。

    參數:
        database_path: DuckDB 資料庫檔案的路徑。
        table_name: 要查詢的資料表名稱。
    """
    con = duckdb.connect(database_path, read_only=True)
    try:
        columns = [row[0] for row in con.execute(f"DESCRIBE {table_name}").fetchall()]
    finally:
        con.close()

    if len(columns) <= 12:
        return ','.join(columns)
    return ','.join(columns[:3]) + '......' + ','.join(columns[-3:])


@tool
def preview_table(database_path: str, table_name: str) -> str:
    """預覽資料表的內容，回傳文字格式的表格預覽。

    最多顯示 6 列、6 欄，並在最後標註資料表實際的列數與欄數。

    參數:
        database_path: DuckDB 資料庫檔案的路徑。
        table_name: 要查詢的資料表名稱。
    """
    con = duckdb.connect(database_path, read_only=True)
    try:
        df = con.execute(f"SELECT * FROM {table_name}").df()
    finally:
        con.close()

    return df.to_string(max_rows=6, max_cols=6, show_dimensions=True)


