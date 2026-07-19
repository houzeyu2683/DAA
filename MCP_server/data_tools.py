from fastmcp import FastMCP
import duckdb
from pathlib import Path
import dotenv
import os

dotenv.load_dotenv()


mcp = FastMCP("data_tools")


@mcp.tool()
def load_table_to_database(table_path: str, database_path: str, table_name: str) -> dict:
    """讀取一份資料表檔案，通常是 CSV 格式，寫入指定的 DuckDB 資料庫，成為一張新的表。
    若資料表已存在，會拒絕執行並回報錯誤，不會覆蓋原有資料。

    參數:
        table_path: 檔案的路徑，通常是 CSV 格式。
        database_path: 要寫入的 DuckDB 資料庫檔案路徑。
        table_name: 寫入後的資料表名稱。
    """

    Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(database_path)
    try:
        exists = con.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
            [table_name],
        ).fetchone()[0] > 0
        if exists:
            return {"error": f"資料表 {table_name} 已存在，未執行載入。"}

        con.execute(
            f"CREATE TABLE {table_name} AS SELECT * FROM read_csv_auto(?)",
            [table_path],
        )
        row_count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        column_count = len(con.execute(f"DESCRIBE {table_name}").fetchall())
    finally:
        con.close()

    return {"database_path": database_path, "table_name": table_name,
            "row_count": row_count, "column_count": column_count}


@mcp.tool()
def check_table_exist(database_path: str, table_name: str) -> bool:
    """檢查指定的資料表是否存在於 DuckDB 資料庫中。"""

    con = duckdb.connect(database_path, read_only=True)
    try:
        count = con.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
            [table_name],
        ).fetchone()[0]
    finally:
        con.close()
    return count > 0



@mcp.tool()
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


if __name__ == "__main__":

    mcp.run(transport="streamable-http", port=8001)


