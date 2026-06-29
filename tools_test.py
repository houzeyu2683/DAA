"""
工具層測試：直接呼叫 tool function，不透過 LLM。
執行：python tools_test.py
"""
import json
import os
from agent.session import Session
from tools_old import sql, pandas_tool, plot

DB_PATH = ".data/workspace.db"
PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"


def check(name, condition, detail=""):
    status = PASS if condition else FAIL
    print(f"  [{status}] {name}" + (f"\n         {detail}" if not condition else ""))
    return condition


def run(name, fn):
    print(f"\n--- {name} ---")
    try:
        fn()
    except Exception as e:
        print(f"  [{FAIL}] 例外: {e}")


session = Session(db_path=DB_PATH)

# ── TC-01 list_tables ─────────────────────────────────────────────────────────
def tc01():
    result = json.loads(sql.list_tables(session))
    check("回傳 tables 欄位", "tables" in result)
    check("包含 my_table", "my_table" in result.get("tables", []))

run("TC-01 list_tables", tc01)

# ── TC-02 describe_table ──────────────────────────────────────────────────────
def tc02():
    result = json.loads(sql.describe_table(session, "my_table"))
    cols = [c["name"] for c in result.get("columns", [])]
    check("包含 Equipment", "Equipment" in cols)
    check("包含 CP_1",      "CP_1" in cols)
    check("包含 CP_300",    "CP_300" in cols)
    check("共 301 欄",      len(cols) == 301, f"實際 {len(cols)} 欄")

run("TC-02 describe_table", tc02)

# ── TC-03 run_sql + save_as ───────────────────────────────────────────────────
def tc03():
    result = json.loads(sql.run_sql(
        session,
        query="SELECT Equipment, CP_1, CP_2, CP_3 FROM my_table",
        save_as="view_cp123"
    ))
    check("無 error",           "error" not in result, result.get("error"))
    check("shape 正確",         result.get("shape") == [2343, 4], result.get("shape"))
    check("view 存進 session",  "view_cp123" in session.views)
    check("DuckDB view 可查",   len(session.con.execute("SELECT * FROM view_cp123 LIMIT 1").fetchdf()) == 1)

run("TC-03 run_sql + save_as", tc03)

# ── TC-04 危險 SQL 守衛 ───────────────────────────────────────────────────────
def tc04():
    for query in [
        "DROP TABLE my_table",
        "DELETE FROM my_table",
        "INSERT INTO my_table VALUES (1)",
    ]:
        result = json.loads(sql.run_sql(session, query))
        check(f"擋住: {query[:30]}", "error" in result)

run("TC-04 危險 SQL 守衛", tc04)

# ── TC-05 merge_views ─────────────────────────────────────────────────────────
def tc05():
    sql.run_sql(session, "SELECT Equipment, CP_10, CP_11 FROM my_table", save_as="view_A")
    sql.run_sql(session, "SELECT Equipment, CP_50, CP_51 FROM my_table", save_as="view_B")
    result = json.loads(sql.merge_views(session, "view_A", "view_B", "Equipment", "view_merged"))
    check("無 error",             "error" not in result, result.get("error"))
    check("view_merged 在 session", "view_merged" in session.views)
    check("欄位包含兩邊",         "CP_10" in result.get("columns", []) and "CP_50" in result.get("columns", []))

run("TC-05 merge_views", tc05)

# ── TC-06 pandas_run ─────────────────────────────────────────────────────────
def tc06():
    result = json.loads(pandas_tool.pandas_run(
        session,
        view_name="view_cp123",
        code="result = df[['CP_1','CP_2','CP_3']].describe()"
    ))
    check("無 error",   "error" not in result, result.get("error"))
    check("有 describe", "describe" in result)

run("TC-06 pandas_run 統計", tc06)

# ── TC-07 pandas_run 自訂計算 ────────────────────────────────────────────────
def tc07():
    result = json.loads(pandas_tool.pandas_run(
        session,
        view_name="view_cp123",
        code="result = df.groupby('Equipment')[['CP_1','CP_2']].mean()"
    ))
    check("無 error", "error" not in result, result.get("error"))
    check("有 preview", "preview" in result)

run("TC-07 pandas_run groupby", tc07)

# ── TC-08 plot ────────────────────────────────────────────────────────────────
def tc08():
    save_path = "/tmp/test_plot.png"
    if os.path.exists(save_path):
        os.remove(save_path)
    result = json.loads(plot.plot(
        session,
        view_name="view_cp123",
        code="df['CP_1'].hist(bins=30); plt.title('CP_1')",
        save_path=save_path
    ))
    check("無 error",   "error" not in result, result.get("error"))
    check("檔案存在",   os.path.exists(save_path))

run("TC-08 plot 存圖", tc08)

# ── TC-09 export_file ─────────────────────────────────────────────────────────
def tc09():
    result = json.loads(sql.export_file(
        session,
        query="SELECT Equipment, CP_1 FROM my_table WHERE CP_1 > 0.5",
        filename="test_export"
    ))
    check("無 error",   "error" not in result, result.get("error"))
    check("檔案存在",   os.path.exists("./exports/test_export.csv"))
    check("size > 0",  result.get("size_mb", 0) > 0)

run("TC-09 export_file", tc09)

# ── TC-10 build_context ───────────────────────────────────────────────────────
def tc10():
    ctx = session.build_context()
    check("context 包含 view_cp123",  "view_cp123" in ctx)
    check("context 包含 view_merged", "view_merged" in ctx)

run("TC-10 build_context", tc10)

print("\n完成。\n")
