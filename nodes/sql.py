from core.status import State
from typing import Dict, TypedDict
from core.functions import getModel
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, filter_messages
import duckdb

model = getModel()

class SQLPlan(TypedDict):
    query: str
    table_name: str
    explanation: str

_planner = model.with_structured_output(SQLPlan)

def getSchema(database: str) -> str:
    con = duckdb.connect(database, read_only=True)
    tables = con.execute("SHOW TABLES").fetchall()
    lines = []
    for (table,) in tables:
        columns = con.execute(f"DESCRIBE {table}").fetchall()
        col_str = ", ".join(f"{col[0]} ({col[1]})" for col in columns)
        lines.append(f"Table: {table}\nColumns: {col_str}")
    con.close()
    return "\n\n".join(lines)

def sql_node(state: State, config: RunnableConfig) -> Dict:
    schema = getSchema(config['configurable']['database'])
    system = SystemMessage(content=f"""你是一個 SQL 生成器，使用 DuckDB 語法。

當前資料庫 schema：
{schema}

規則：
- query 只輸出純 SELECT 語句，不可包含 CREATE、DROP、INSERT 等語句
- table_name 是這次查詢結果要存成的表格名稱，用英文，格式為 result_xxx
- explanation 用繁體中文說明這個查詢做什麼
- 需要過濾、排序、分組、取 TOP N 等操作，直接用 WHERE、ORDER BY、GROUP BY、LIMIT、子查詢完成，不要留給後續步驟處理
""")

    conversation_history = filter_messages(state["messages"], include_types=["human", "ai"])
    conversation = conversation_history[-4:]
    
    task = state["tasks"][0]
    
    content = [system] + conversation + [HumanMessage(f"任務：{task['description']}")]
    res = _planner.invoke(content)

    ## query 錯誤情況要處理
    con = duckdb.connect(config['configurable']['database'])
    con.execute(f'CREATE TABLE {res["table_name"]} AS {res["query"]}')
    con.close()

    return {
        "tasks": state["tasks"][1:],   # 移除當前 task
        "tables": [{"name": res["table_name"], "description": res["explanation"]}],  # 新增這張表的指標
        "messages": [AIMessage(content=f"[SQL] {res['explanation']}，結果存為 {res['table_name']}")]  # 告訴 LLM 做了什麼
    }
