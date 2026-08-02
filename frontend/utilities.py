from pathlib import Path

import chainlit as cl
import duckdb


def is_files_in_user_message(user_message: cl.Message) -> bool:
    """檢查這則使用者訊息有沒有附加檔案。"""

    return len(user_message.elements) > 0


# def get_file_names(user_message: cl.Message) -> list[str]:
#     """取得這則使用者訊息附加的所有檔案名稱。"""

#     return [element.name for element in user_message.elements if element.name]


def create_database(database_path: str) -> bool:
    """新增一個 DuckDB 資料庫，資料夾不存在會一併建立。"""

    Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(database_path)
    connection.close()
    return True


def create_table_with_file_path(database_path: str, table_name: str, file_path: str) -> bool:
    """把指定路徑的 CSV 檔案讀進資料庫，建立成一張資料表。"""

    connection = duckdb.connect(database_path)
    connection.execute(
        f'CREATE OR REPLACE TABLE "{table_name}" AS SELECT * FROM read_csv_auto(?)',
        [file_path],
    )
    connection.close()
    return True
