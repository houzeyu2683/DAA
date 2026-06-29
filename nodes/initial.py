import duckdb
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig

from core.status import State

"""
這裡有兩種情境
- 用戶對上傳的表不清楚，他想理解表格概況
- 用戶對上傳的表理解夠，它想做一些分析操作
以上這兩種狀況都可以透過下面的任務編排來試著完成
"""


def initial_node(state: State, config: RunnableConfig) -> dict:

    if state['messages'] ==[] and state['tables'] ==[]:
        print("state is empty")

    database = config['configurable']['database']
    con = duckdb.connect(database)
    tables = con.execute("SHOW TABLES").fetchdf()
    table_entries = []
    schema_lines = []
    for table in tables['name'].tolist():
        columns = con.execute(f"DESCRIBE {table}").fetchdf()
        row_count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        n_cols = len(columns)
        schema_lines.append(f"- {table}：{row_count} 列 x {n_cols} 欄")
        table_entries.append({"name": table, "description": f"{row_count} 列 x {n_cols} 欄"})
    con.close()
    schema_text = "\n".join(schema_lines)

    content = f"你是一個資料分析助理。目前資料庫有以下表格：\n{schema_text}"
    system = SystemMessage(content=content)
    return {"messages": [system], "tables": table_entries}
