"""
示範：如何用 session + DuckDB temp view 讓 agent 記住處理過的表

核心概念：
  - session dict  → 記住「有哪些 view」（給 LLM 看的文字狀態）
  - DuckDB view   → 記住「資料本身」（給 SQL 用的資料狀態）
  - build_context → 每輪對話注入當前狀態，讓 LLM 不用翻歷史
"""

import json
import duckdb

# ─── 模擬環境 ────────────────────────────────────────────────────────────────

con = duckdb.connect(":memory:")

# 建兩張假表
con.execute("""
    CREATE TABLE tableA AS
    SELECT 'machine_' || (i % 5 + 1) AS Equipment,
           random() AS CB_22,
           random() AS cp_eq1,
           random() AS cp_eq2
    FROM range(100) t(i)
""")
con.execute("""
    CREATE TABLE tableB AS
    SELECT 'machine_' || (i % 5 + 1) AS Equipment,
           random() AS CB_22,
           random() AS wat_eq1,
           random() AS wat_eq2
    FROM range(100) t(i)
""")

# ─── Session 狀態 ─────────────────────────────────────────────────────────────

session = {
    "views": {}
    # 格式: { "view_name": "這個 view 代表什麼" }
}

# ─── Tools ───────────────────────────────────────────────────────────────────

def run_sql(query: str, save_as: str = None) -> str:
    """
    執行 SQL，可選擇把結果存成 view。

    save_as: 如果提供，就建一個 DuckDB temp view 並記錄到 session。
    """
    try:
        preview = con.execute(query).fetchdf().head(5)

        # 如果要存成 view
        if save_as:
            con.execute(f"CREATE OR REPLACE VIEW {save_as} AS {query}")
            session["views"][save_as] = f"來自查詢: {query[:60]}..."
            print(f"  [已建立 view: {save_as}]")

        return json.dumps({
            "columns": list(preview.columns),
            "preview": preview.to_dict(orient="records"),
            "saved_as": save_as
        }, ensure_ascii=False, default=str)

    except Exception as e:
        return json.dumps({"error": str(e)})


def merge_views(view1: str, view2: str, on: str, save_as: str) -> str:
    """把兩個 view JOIN 起來，存成新的 view。"""
    query = f"SELECT * FROM {view1} JOIN {view2} USING ({on})"
    try:
        con.execute(f"CREATE OR REPLACE VIEW {save_as} AS {query}")
        session["views"][save_as] = f"{view1} JOIN {view2} ON {on}"
        print(f"  [已建立合併 view: {save_as}]")
        preview = con.execute(f"SELECT * FROM {save_as} LIMIT 5").fetchdf()
        return json.dumps({
            "columns": list(preview.columns),
            "preview": preview.to_dict(orient="records"),
            "saved_as": save_as
        }, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ─── Context 注入 ─────────────────────────────────────────────────────────────

def build_context() -> str:
    """
    每輪對話前重新產生，把當前 session 狀態告訴 LLM。
    這樣 LLM 不需要翻歷史對話就知道有哪些 view 可以用。
    """
    if not session["views"]:
        return "目前 session 中沒有已儲存的 view。"

    lines = ["目前 session 中已有以下 view 可直接使用："]
    for name, desc in session["views"].items():
        lines.append(f"  - {name}：{desc}")
    return "\n".join(lines)


# ─── 模擬多輪對話 ─────────────────────────────────────────────────────────────

def show_session():
    print(f"\n  [當前 session]: {session['views']}\n")


if __name__ == "__main__":
    print("=" * 60)
    print("模擬對話：用戶跨多輪查詢兩張表，最後合併")
    print("=" * 60)

    # 輪次 1：查 tableB 的部分欄位，存成 view
    print("\n[輪次 1] 用戶：我想看 tableB 的 CB_22 跟 wat_eq*")
    result = run_sql(
        "SELECT Equipment, CB_22, wat_eq1, wat_eq2 FROM tableB",
        save_as="view_tableB"
    )
    print(f"  context 給 LLM 看：\n  {build_context()}")
    show_session()

    # 輪次 2：切換去看 tableA，存成 view
    print("[輪次 2] 用戶：我想看 tableA 的 CB_22 跟 cp_eq*")
    result = run_sql(
        "SELECT Equipment, CB_22, cp_eq1, cp_eq2 FROM tableA",
        save_as="view_tableA"
    )
    print(f"  context 給 LLM 看：\n  {build_context()}")
    show_session()

    # 輪次 3：用戶回去看 tableB（LLM 知道 view_tableB 還在）
    print("[輪次 3] 用戶：我想回去看一下剛才 tableB 的資料")
    result = run_sql("SELECT * FROM view_tableB LIMIT 3")
    data = json.loads(result)
    print(f"  直接查 view_tableB，不需要重新指定欄位")
    print(f"  欄位：{data['columns']}")
    show_session()

    # 輪次 4：合併兩張表
    print("[輪次 4] 用戶：把兩張表合併")
    result = merge_views("view_tableA", "view_tableB", on="Equipment", save_as="view_merged")
    print(f"  context 給 LLM 看：\n  {build_context()}")
    show_session()
