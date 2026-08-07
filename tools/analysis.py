import duckdb


def calculate_similarity(
    database_path: str,
    table_name: str,
    dependent_numeric_column_name: str,
    response_numeric_column_name: str,
    result_table_name: str
) -> dict:
    """計算指定資料表中兩個數值欄位的相似度(皮爾森相關係數),結果存成新的資料表寫回資料庫。"""

    database_path = database_path.strip('"').strip("'")
    table_name = table_name.strip('"').strip("'")
    dependent_numeric_column_name = dependent_numeric_column_name.strip('"').strip("'")
    response_numeric_column_name = response_numeric_column_name.strip('"').strip("'")
    result_table_name = result_table_name.strip('"').strip("'")

    connection = duckdb.connect(database=database_path)

    connection.execute(f"""
        CREATE OR REPLACE TABLE {result_table_name} AS
        SELECT corr({dependent_numeric_column_name}, {response_numeric_column_name}) AS similarity
        FROM {table_name}
    """)
    connection.close()

    return {
        "dependent_numeric_column_name": dependent_numeric_column_name,
        "response_numeric_column_name": response_numeric_column_name,
        "result_table_name": result_table_name
    }
