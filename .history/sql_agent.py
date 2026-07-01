import os
import json
import duckdb
import dotenv
import os
from openai import OpenAI

# ===== 設定 =====
_ = dotenv.load_dotenv()
client = OpenAI(
    base_url=os.getenv('base_url'),  # 換成你的 vLLM endpoint
    api_key=os.getenv('api_key')
)
MODEL = os.getenv("MODEL_NAME")  # 換成你的模型名稱
con = duckdb.connect(".data/workspace.db")  # 換成你的 DuckDB 路徑

# ===== System Prompt =====
SYSTEM_PROMPT = """你是一個資料庫助理。
你有以下工具可以使用：
- list_tables：只在用戶問「有哪些表」時使用
- get_columns：只在用戶問「某張表有哪些欄位」時使用，直接用表名呼叫，不需要先呼叫 list_tables
- run_sql：查詢資料、篩選欄位、合併表格時使用
- export_file：用戶要儲存或下載資料時使用

規則：
1. 不要重複呼叫同一個 tool
2. 拿到 tool 結果後直接回答用戶
3. 需求不明確時，先提供建議再詢問用戶
"""

# ===== Tool 函數 =====
def list_tables() -> str:
    """列出所有表"""
    result = con.execute("SHOW TABLES").fetchall()
    tables = [row[0] for row in result]
    return json.dumps({"tables": tables}, ensure_ascii=False)

def get_columns(table_name: str) -> str:
    """取得指定表的所有欄位名稱與型別"""
    result = con.execute(f"DESCRIBE {table_name}").fetchall()
    columns = [{"name": row[0], "type": row[1]} for row in result]
    return json.dumps({"table": table_name, "columns": columns}, ensure_ascii=False)

def run_sql(query: str) -> str:
    """執行 SQL 查詢，只回傳預覽，不把資料載入記憶體"""
    forbidden = ["drop", "delete", "update", "insert", "alter"]
    if any(word in query.lower() for word in forbidden):
        return json.dumps({"error": "只允許 SELECT 查詢"})
    try:
        # 估算資料量
        count = con.execute(f"SELECT COUNT(*) FROM ({query}) AS _c").fetchone()[0]
        col_count = len(con.execute(f"SELECT * FROM ({query}) AS _c LIMIT 1").fetchdf().columns)
        estimated_mb = round((count * col_count * 8) / (1024 * 1024), 2)

        if estimated_mb > 500:
            return json.dumps({
                "error": f"查詢資料量太大（約 {estimated_mb} MB），超過 500 MB 限制",
                "suggestion": "建議加上 WHERE 條件、減少欄位，或直接使用 export_file 匯出"
            })

        # 只撈預覽
        preview = con.execute(f"SELECT * FROM ({query}) AS _p LIMIT 100").fetchdf()
        return json.dumps({
            "total_rows": count,
            "estimated_mb": estimated_mb,
            "preview_rows": len(preview),
            "columns": list(preview.columns),
            "data": preview.to_dict(orient="records")
        }, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})

def export_file(query: str, filename: str) -> str:
    """將查詢結果直接寫入 CSV，不佔用記憶體"""
    forbidden = ["drop", "delete", "update", "insert", "alter"]
    if any(word in query.lower() for word in forbidden):
        return json.dumps({"error": "只允許 SELECT 查詢"})
    try:
        os.makedirs("./exports", exist_ok=True)
        filepath = f"./exports/{filename}.csv"
        con.execute(f"COPY ({query}) TO '{filepath}' (HEADER, DELIMITER ',')")
        size_mb = round(os.path.getsize(filepath) / (1024 * 1024), 2)
        return json.dumps({
            "status": "完成",
            "filepath": filepath,
            "size_mb": size_mb
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

# ===== Tool 註冊表（新增 tool 只需改這裡）=====
TOOL_FUNCTIONS = {
    "list_tables": list_tables,
    "get_columns": get_columns,
    "run_sql": run_sql,
    "export_file": export_file,
}

# ===== Tool 描述（給 LLM 看）=====
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_tables",
            "description": "列出資料庫中所有可用的表",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_columns",
            "description": "取得指定表的所有欄位名稱與資料型別。當用戶想知道某張表有哪些欄位時，直接呼叫此 tool，不需要先呼叫 list_tables。",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "表的名稱，例如 iot_telemetry_data"
                    }
                },
                "required": ["table_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_sql",
            "description": "對資料庫執行 SQL SELECT 查詢並回傳結果預覽。用戶想看資料、篩選欄位、合併表格時使用。預覽資料時自行加上 LIMIT，只允許 SELECT。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "要執行的 SQL SELECT 語句"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "export_file",
            "description": "將 SQL 查詢結果匯出成 CSV 檔案供用戶下載。資料量大時使用此 tool，不會佔用記憶體。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "要匯出的 SQL SELECT 語句"
                    },
                    "filename": {
                        "type": "string",
                        "description": "輸出檔案名稱，不含副檔名，例如 result_20240101"
                    }
                },
                "required": ["query", "filename"]
            }
        }
    }
]

# ===== Tool 執行器（不用再動這裡）=====
def execute_tool(tool_name: str, tool_args: dict) -> str:
    if tool_name not in TOOL_FUNCTIONS:
        return json.dumps({"error": f"未知的 tool: {tool_name}"})
    return TOOL_FUNCTIONS[tool_name](**tool_args)

# ===== 對話歷史（多輪對話共用）=====
messages = []

# ===== Agent 主迴圈（不用再動這裡）=====
def run_agent(user_message: str):
    messages.append({"role": "user", "content": user_message})
    max_steps = 10
    step = 0

    while True:
        if step >= max_steps:
            print("[已達最大步驟數，停止]")
            break
        step += 1

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
            tools=TOOLS,
            tool_choice="auto"
        )

        msg = response.choices[0].message

        # LLM 決定直接回答
        if not msg.tool_calls:
            print(f"AI: {msg.content}")
            messages.append({"role": "assistant", "content": msg.content})
            break

        # LLM 決定呼叫 tool
        messages.append(msg)

        for tool_call in msg.tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)

            print(f"[呼叫 tool: {tool_name} | 參數: {tool_args}]")
            result = execute_tool(tool_name, tool_args)
            print(f"[tool 結果: {result}]")

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })

# ===== 對話入口 =====
if __name__ == "__main__":
    print("SQL Agent 啟動，輸入 'exit' 離開")
    while True:
        user_input = input("\n你：").strip()
        if user_input.lower() == "exit":
            break
        if not user_input:
            continue
        run_agent(user_input)
