import re
from pathlib import Path

import duckdb
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("DATA Server", host="0.0.0.0", port=8001)


def _sanitize_table_name(name: str) -> str:
    name = re.sub(r"[^0-9a-zA-Z_]", "_", name).strip("_") or "table"
    if name[0].isdigit():
        name = f"t_{name}"
    return name.lower()


@mcp.tool()
def load_csv_to_table(source: str, workspace: str, database: str) -> dict:
    """讀取 CSV 檔案，將原始資料完整存入使用者的個人資料庫，回傳存入的表名與摘要。"""
    workspace_dir = Path(workspace)
    workspace_dir.mkdir(parents=True, exist_ok=True)
    db_path = workspace_dir / database

    table_name = f"raw_{_sanitize_table_name(Path(source).stem)}"

    con = duckdb.connect(str(db_path))
    try:
        con.execute(
            f'CREATE TABLE "{table_name}" AS SELECT * FROM read_csv_auto(?)',
            [source],
        )
    finally:
        con.close()

    # sample_size = 10
    return {
        "table_name": table_name,
        "database": str(db_path),
        # "row_count": row_count,
        # "column_count": len(columns),
        # "column_sample": columns[:sample_size],
        "description": f"資料已完整存入資料庫 '{db_path}' 的表 '{table_name}' 中"
        # "description": (
        #     f"已完整存入資料庫 '{db_path}' 的表 '{table_name}' 中"
        #     # f"共 {row_count} 筆、{len(columns)} 個欄位"
        #     # f"（例如：{', '.join(columns[:sample_size])}{' ...' if len(columns) > sample_size else ''}）。"
        # ),
    }


if __name__ == "__main__":
    mcp.run(transport="sse")
