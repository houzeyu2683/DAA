import os
import re
import duckdb


def is_file_exist(file_path: str) -> bool:
    """檢查檔案是否存在。"""

    file_path = file_path.strip('"').strip("'")
    return os.path.isfile(file_path)


def is_folder_exist(folder_path: str) -> bool:
    """檢查資料夾是否存在。"""

    folder_path = folder_path.strip('"').strip("'")
    return os.path.isdir(folder_path)


def list_table_names(database_path: str, number_index: int = 0, offset_index: int = 10) -> dict:
    """列出資料庫裡有哪些資料表。"""

    database_path = database_path.strip('"').strip("'")
    connection = duckdb.connect(database=database_path)
    all_table_names = connection.execute("SHOW TABLES").fetchall()
    connection.close()
    table_names = all_table_names[number_index: number_index+offset_index]
    all_table_names_total = len(table_names)
    return {
        "table_names": table_names,
        "all_table_names_total": all_table_names_total
    }


def search_column(
    database_path: str,
    table_name: str,
    regular_expression: str,
    number_index: int = 0,
    offset_index: int = 10,
) -> dict:
    """用正規表達式搜尋指定資料表裡符合的欄位名稱與型態,為了避免過長,預設指定一個索引範圍。"""

    database_path = database_path.strip('"').strip("'")
    table_name = table_name.strip('"').strip("'")

    connection = duckdb.connect(database=database_path, read_only=True)
    all_columns = connection.execute(f"DESCRIBE {table_name}").fetchall()
    connection.close()

    pattern = re.compile(regular_expression)
    matched_columns = [
        (name, column_type) for name, column_type, *_ in all_columns
        if pattern.search(name)
    ]
    search_column_total = len(matched_columns)
    page = matched_columns[number_index: number_index + offset_index]

    return {
        "search_column_total": search_column_total,
        "search_column_names": [name for name, _ in page],
        "search_column_type": [column_type for _, column_type in page],
        "number_index": number_index,
        "offset_index": offset_index,
    }