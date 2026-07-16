import pandas as pd
from mcp.server.fastmcp import FastMCP

from tools.default import (
    check_file_exist,
    check_database_exist,
    create_database,
    check_table_exist,
    create_table,
    list_tables,
)

mcp = FastMCP("data-tools")

mcp.tool()(check_file_exist.func)
mcp.tool()(check_database_exist.func)
mcp.tool()(create_database.func)
mcp.tool()(check_table_exist.func)
mcp.tool()(list_tables.func)


@mcp.tool()
def load_table_to_database(table_path: str, database_path: str, table_name: str) -> dict:
    """讀取一份資料表檔案，通常是 CSV 格式，寫入指定的 DuckDB 資料庫，成為一張新的表。

    參數:
        table_path: 檔案的路徑，通常是 CSV 格式。
        database_path: 要寫入的 DuckDB 資料庫檔案路徑。
        table_name: 寫入後的資料表名稱。
    """
    table_content = pd.read_csv(table_path)
    row_count, _ = table_content.shape
    created_table = create_table.invoke({
        "database_path": database_path,
        "table_name": table_name,
        "table_content": table_content,
    })
    return {"table_name": table_name, "row_count": row_count, "created_table": created_table}


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
