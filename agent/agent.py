import os
import json
import dotenv
from openai import OpenAI
from agent.session import Session
from tools import sql, pandas_tool, plot

_ = dotenv.load_dotenv()
client = OpenAI(
    base_url=os.getenv("base_url"),
    api_key=os.getenv("api_key")
)
MODEL = os.getenv("MODEL_NAME")

_SYSTEM_PROMPT = """你是一個資料分析助理。
你有以下工具可以使用：
- list_tables：列出所有可用的表
- describe_table：查看指定表的欄位結構
- run_sql：執行 SQL 查詢，可選擇將結果存成 view
- merge_views：將兩個 view JOIN 合併成新的 view
- export_file：將查詢結果匯出成 CSV
- pandas_run：對指定 view 執行 pandas 分析
- plot：對指定 view 畫圖並儲存

規則：
1. 資料量大時，一定要在 SQL 層先 filter/aggregate，不要把整張表拿進來
2. 不要重複呼叫同一個 tool（除非用戶要求重新查詢）
3. 拿到 tool 結果後直接回答用戶
4. 需求不明確時，先提供建議再詢問用戶

{session_context}
"""

_TOOL_FUNCTIONS = {
    "list_tables":   sql.list_tables,
    "describe_table": sql.describe_table,
    "run_sql":       sql.run_sql,
    "merge_views":   sql.merge_views,
    "export_file":   sql.export_file,
    "pandas_run":    pandas_tool.pandas_run,
    "plot":          plot.plot,
}

_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_tables",
            "description": "列出資料庫中所有可用的表",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "describe_table",
            "description": "取得指定表的欄位名稱與資料型別",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {"type": "string", "description": "表的名稱"}
                },
                "required": ["table_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_sql",
            "description": "執行 SQL SELECT 查詢。用 save_as 把結果存成 view 供後續使用。資料量大時一定要 GROUP BY 或 WHERE 縮小範圍。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "SQL SELECT 語句"},
                    "save_as": {"type": "string", "description": "選填，將結果存成此名稱的 view"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "merge_views",
            "description": "將兩個 view JOIN 合併成新的 view",
            "parameters": {
                "type": "object",
                "properties": {
                    "view1": {"type": "string", "description": "第一個 view 名稱"},
                    "view2": {"type": "string", "description": "第二個 view 名稱"},
                    "on":    {"type": "string", "description": "JOIN 使用的欄位名稱"},
                    "save_as": {"type": "string", "description": "合併後的 view 名稱"}
                },
                "required": ["view1", "view2", "on", "save_as"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "export_file",
            "description": "將 SQL 查詢結果匯出成 CSV 檔案，不會佔用記憶體，適合大資料量",
            "parameters": {
                "type": "object",
                "properties": {
                    "query":    {"type": "string", "description": "要匯出的 SQL SELECT 語句"},
                    "filename": {"type": "string", "description": "輸出檔案名稱，不含副檔名"}
                },
                "required": ["query", "filename"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "pandas_run",
            "description": "對指定 view 執行 pandas 分析，回傳統計摘要。程式碼可使用 df 和 pd，分析結果存在 result 變數。",
            "parameters": {
                "type": "object",
                "properties": {
                    "view_name": {"type": "string", "description": "要分析的 view 名稱"},
                    "code":      {"type": "string", "description": "pandas 分析程式碼"}
                },
                "required": ["view_name", "code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "plot",
            "description": "對指定 view 的資料畫圖並儲存。程式碼可使用 df 和 plt。",
            "parameters": {
                "type": "object",
                "properties": {
                    "view_name": {"type": "string", "description": "要畫圖的 view 名稱"},
                    "code":      {"type": "string", "description": "matplotlib 畫圖程式碼"},
                    "save_path": {"type": "string", "description": "圖片儲存路徑，例如 ~/Desktop/result.png"}
                },
                "required": ["view_name", "code", "save_path"]
            }
        }
    },
]


def run_agent(session: Session, user_message: str):
    session.messages.append({"role": "user", "content": user_message})

    system_prompt = _SYSTEM_PROMPT.format(
        session_context=f"當前 session 狀態：\n{session.build_context()}"
    )

    for step in range(10):
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": system_prompt}] + session.messages,
            tools=_TOOLS,
            tool_choice="auto"
        )
        msg = response.choices[0].message

        if not msg.tool_calls:
            print(f"\nAI: {msg.content}")
            session.messages.append({"role": "assistant", "content": msg.content})
            return

        session.messages.append(msg)

        for tool_call in msg.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)

            print(f"  [tool: {name} | 參數: {args}]")
            result = _TOOL_FUNCTIONS[name](session, **args)
            preview = result[:200] + "..." if len(result) > 200 else result
            print(f"  [結果: {preview}]")

            session.messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })

    print("[已達最大步驟數，停止]")
