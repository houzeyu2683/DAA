"""
單獨測試各 node，不走完整 graph。
執行：conda run -n DAA python test_nodes.py
"""
import os
import duckdb
import pandas as pd
from uuid import uuid4
from os import makedirs
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from core.status import State
from spec.sql import sql_node
from spec.stats import stats_node
from spec.plot import plot_node

# ── 建立測試環境 ────────────────────────────────────────────────────────────────
user_id = uuid4().hex[:4]
thread_id = uuid4().hex[:4]
workspace = f'./.data/workspace/{user_id}/{thread_id}'
database = f'{workspace}/database.db'
makedirs(workspace, exist_ok=True)

df = pd.read_csv('./.data/sample.csv')
con = duckdb.connect(database)
con.register('tmp', df)
con.execute("CREATE TABLE sample AS SELECT * FROM tmp")
con.unregister('tmp')
con.close()

config = {
    'configurable': {
        'user_id': user_id,
        'thread_id': thread_id,
        'workspace': workspace,
        'database': database,
    }
}

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"


def make_state(task_type: str, description: str, extra_messages=None) -> State:
    messages = [
        SystemMessage(content="你是資料分析助理。資料庫有 sample 表，欄位：Equipment, CP_1~CP_300。"),
        HumanMessage(content=description),
    ]
    if extra_messages:
        messages += extra_messages
    return State(
        messages=messages,
        tables=[{"name": "sample", "description": "2343 列 x 301 欄"}],
        intent="plan",
        tasks=[{"type": task_type, "description": description}],
    )


# ── TC-01 sql_node ──────────────────────────────────────────────────────────────
print("\n=== TC-01 sql_node ===")
try:
    state = make_state("sql", "從 sample 撈出 Equipment 和 CP_1、CP_2、CP_3 三欄，存成 view")
    result = sql_node(state, config)
    msgs = [m for m in result['messages'] if isinstance(m, AIMessage)]
    content = msgs[-1].content if msgs else ""
    ok = "SQL" in content and "失敗" not in content
    print(f"[{PASS if ok else FAIL}] {content[:200]}")

    # 確認 view 是否真的存在
    con = duckdb.connect(database)
    views = con.execute("SELECT table_name FROM information_schema.tables WHERE table_type='VIEW'").fetchdf()
    con.close()
    print(f"  Views in DB: {views['table_name'].tolist()}")
except Exception as e:
    print(f"[{FAIL}] 例外：{e}")


# ── TC-02 stats_node ────────────────────────────────────────────────────────────
print("\n=== TC-02 stats_node ===")
try:
    # 先確保有個 view 可以用
    con = duckdb.connect(database)
    con.execute("CREATE OR REPLACE VIEW view_cp3 AS SELECT Equipment, CP_1, CP_2, CP_3 FROM sample")
    con.close()

    state = make_state("stats", "對 view_cp3 計算每個 Equipment 的 CP_1 平均值，找出平均最高的三台機器")
    result = stats_node(state, config)
    msgs = [m for m in result['messages'] if isinstance(m, AIMessage)]
    content = msgs[-1].content if msgs else ""
    ok = "Stats" in content and "失敗" not in content
    print(f"[{PASS if ok else FAIL}] {content[:300]}")
except Exception as e:
    print(f"[{FAIL}] 例外：{e}")


# ── TC-03 plot_node ─────────────────────────────────────────────────────────────
print("\n=== TC-03 plot_node ===")
try:
    # 先確保有個 view 可以用
    con = duckdb.connect(database)
    con.execute("CREATE OR REPLACE VIEW view_cp3 AS SELECT Equipment, CP_1, CP_2, CP_3 FROM sample")
    con.close()

    state = make_state("plot", "對 view_cp3 畫 CP_1 的 histogram")
    result = plot_node(state, config)
    msgs = [m for m in result['messages'] if isinstance(m, AIMessage)]
    content = msgs[-1].content if msgs else ""
    ok = "Plot" in content and "失敗" not in content
    print(f"[{PASS if ok else FAIL}] {content[:200]}")

    # 確認圖片是否存在
    plot_path = f"{workspace}/plot.png"
    print(f"  Plot file exists: {os.path.exists(plot_path)}")
except Exception as e:
    print(f"[{FAIL}] 例外：{e}")

print("\n完成。\n")
