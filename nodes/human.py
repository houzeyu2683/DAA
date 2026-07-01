from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import interrupt
from core.status import State
import duckdb

def human_node(state: State, config: RunnableConfig) -> dict:

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

    content = f"你是一個SQL資料分析助理。目前 duckdb 資料庫有以下表格：\n{schema_text}，用戶接下來會跟你提出需求，你需要熟悉 duckDB 語法以及正規語法來協助用戶完成大數據任務"
    system = SystemMessage(content=content)


    content = interrupt("用戶輸入")
    return {"messages": [system, HumanMessage(content)]}