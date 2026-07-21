import os
import duckdb as db
from pathlib import Path
from langchain.tools import tool


@tool
def is_file_exist(file_path: str) -> bool:
    """檢查檔案是否存在。"""
    return os.path.isfile(file_path)


@tool
def create_database(database_path: str) -> bool:
    """新增一個資料庫。"""
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    con = db.connect(database_path)
    con.close()
    return True


@tool
def create_table(database_path: str, table_name: str, table_path: str) -> bool:
    """新增一張資料表。"""
    con = db.connect(database_path)
    try:
        con.execute(
            f"CREATE TABLE {table_name} AS SELECT * FROM read_csv_auto(?)",
            [table_path],
        )
        exists = con.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
            [table_name],
        ).fetchone()[0] > 0
    finally:
        con.close()
    return exists


@tool
def is_columns_exist(database_path: str, table_name: str, column_names: list) -> dict:
    """檢查欄位是否存在於資料表中。

    範例：{'user_id': True, 'user_name': False}
    """
    con = db.connect(database_path, read_only=True)
    try:
        existing_columns = {
            row[0] for row in con.execute(f"DESCRIBE {table_name}").fetchall()
        }
    finally:
        con.close()
    return {name: name in existing_columns for name in column_names}


def search_types_distribution_with_pattern(database_path: str, table_name: str, column_patterns: dict) -> dict:
    """依照欄位名稱的比對模式，回傳符合欄位的資料型別分佈。

    column_patterns 格式為 {'欄位名稱': '比對模式'}，比對模式可以是：
        - equals：完全相符，例如 {'user_id': 'equals'}
        - contains：包含子字串，例如 {'user_id': 'contains'}
        - starts：開頭符合，例如 {'user_id': 'starts'}
        - ends：結尾符合，例如 {'user_id': 'ends'}

    也可以一次指定多個欄位規則，例如 {'user_id': 'ends', 'user_na': 'contains'}。
    """
    pass


@tool
def select_columns(database_path: str, table_name: str, column_names: list, checkpoint_name: str) -> dict:
    """查詢指定欄位，並將查詢結果另存為一個檢查點（checkpoint）表格。"""
    con = db.connect(database_path)
    try:
        columns_clause = ", ".join(column_names)
        con.execute(
            f"CREATE OR REPLACE TABLE {checkpoint_name} AS SELECT {columns_clause} FROM {table_name}"
        )
        row_count = con.execute(f"SELECT COUNT(*) FROM {checkpoint_name}").fetchone()[0]
    finally:
        con.close()
    return {
        "checkpoint_name": checkpoint_name,
        "row_count": row_count,
        "column_count": len(column_names),
    }


@tool
def preview_table(database_path: str, table_name: str) -> dict:
    """預覽資料表內容。"""
    con = db.connect(database_path, read_only=True)
    try:
        rows_count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        df = con.execute(f"SELECT * FROM {table_name} LIMIT 20").fetchdf()
        columns_count = df.shape[1]
    finally:
        con.close()
    table_preview = df.to_string(max_rows=6, max_cols=6, show_dimensions=False)
    return {
        "columns_count": columns_count,
        "rows_count": rows_count,
        "table_preview": table_preview,
    }


@tool
def export_table(database_path: str, table_name: str, table_path: str) -> bool:
    """將資料表從資料庫匯出成檔案。"""
    Path(table_path).parent.mkdir(parents=True, exist_ok=True)
    con = db.connect(database_path, read_only=True)
    try:
        con.execute(
            f"COPY (SELECT * FROM {table_name}) TO ? (FORMAT CSV, HEADER)",
            [table_path],
        )
    finally:
        con.close()
    return True
