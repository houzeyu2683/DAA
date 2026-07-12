import re
from pathlib import Path

import duckdb
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("STATS Server", host="0.0.0.0", port=8002)



@mcp.tool()
def anova_tool(workspace: str, database: str, table: str, target_column: str, pattern: str) -> dict:
    """"""
    workspace_dir = Path(workspace)
    workspace_dir.mkdir(parents=True, exist_ok=True)
    db_path = workspace_dir / database

    ##  to do 
    return

if __name__ == "__main__":
    mcp.run(transport="sse")
