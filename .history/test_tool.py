"""
執行：python test_tool.py
"""
import duckdb
import tempfile
import os
from tools.default import get_schema

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"


def check(name, condition, detail=""):
    status = PASS if condition else FAIL
    print(f"  [{status}] {name}" + (f"\n         {detail}" if not condition else ""))


def run(name, fn):
    print(f"\n--- {name} ---")
    try:
        fn()
    except Exception as e:
        print(f"  [{FAIL}] 例外: {e}")


# 建立測試用 DB
def make_test_db():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    con = duckdb.connect(tmp.name)
    con.execute("CREATE TABLE sample (Equipment VARCHAR, CP_1 DOUBLE, CP_2 DOUBLE)")
    con.close()
    return tmp.name


DB = make_test_db()


# ── TC-01 正常取得 schema ──────────────────────────────────────────────────────
def tc01():
    result = get_schema(DB, "sample")
    check("無 error",         "error" not in result)
    check("table 名稱正確",   result.get("table") == "sample")
    cols = [c["name"] for c in result.get("columns", [])]
    check("包含 Equipment",   "Equipment" in cols)
    check("包含 CP_1",        "CP_1" in cols)
    check("共 3 欄",          len(cols) == 3, f"實際 {len(cols)} 欄")

run("TC-01 get_schema 正常", tc01)


# ── TC-02 table 不存在 ────────────────────────────────────────────────────────
def tc02():
    result = get_schema(DB, "not_exist")
    check("回傳 error",       "error" in result)

run("TC-02 get_schema table 不存在", tc02)


# ── TC-03 LLM 呼叫 get_schema tool ───────────────────────────────────────────
def tc03():
    from openai import OpenAI
    from dotenv import load_dotenv
    import json

    load_dotenv()
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPEN_ROUTER_API_KEY"),
    )

    tool_def = {
        "type": "function",
        "function": {
            "name": "get_schema",
            "description": "取得 DuckDB 資料表的欄位結構",
            "parameters": {
                "type": "object",
                "properties": {
                    "database": {"type": "string", "description": "DuckDB 檔案路徑"},
                    "table_name": {"type": "string", "description": "資料表名稱"},
                },
                "required": ["database", "table_name"],
            },
        },
    }

    response = client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=[{"role": "user", "content": f"請查詢資料庫 {DB} 裡 sample 資料表的欄位結構。"}],
        tools=[tool_def],
        tool_choice="auto",
    )

    msg = response.choices[0].message
    check("LLM 有回傳 tool_calls", bool(msg.tool_calls), "LLM 未呼叫任何 tool")

    if not msg.tool_calls:
        return

    call = msg.tool_calls[0]
    check("tool 名稱為 get_schema", call.function.name == "get_schema",
          f"實際 tool: {call.function.name}")

    args = json.loads(call.function.arguments)
    check("arguments 包含 table_name", "table_name" in args, f"args: {args}")

    result = get_schema(args.get("database", DB), args["table_name"])
    check("執行後無 error",       "error" not in result)
    check("table 名稱正確",       result.get("table") == "sample")
    cols = [c["name"] for c in result.get("columns", [])]
    check("包含 Equipment",       "Equipment" in cols)

run("TC-03 LLM tool calling get_schema", tc03)


# 清理
os.unlink(DB)
print("\n完成。\n")
