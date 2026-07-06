'''
學習：讓 agent 用 tool

三個節點：
1. human：讓用戶輸入
2. agent：呼叫 model.invoke，model 有綁定 tool，會自己決定要不要呼叫
3. END

如果 agent 決定呼叫 tool，會先跑 tools 節點執行，再回到 agent 讓它看到結果、組出最終回覆。
'''

import duckdb
import fnmatch
import pandas as pd
from pathlib import Path
from scipy import stats as scipy_stats
from uuid import uuid4
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command

from core import getModel
from core.status import State

DATABASE = './.data/workspace.db'
RESULTS_DIR = './.data/results'


@tool
def select_columns(table: str, columns: list[str]) -> str:
    """從資料庫中指定的表格裡挑出欄位。columns 每一項可以是精確欄位名稱（例如 "CP_2"），
    也可以用萬用字元 * 做模糊比對：開頭是 CP_ 用 "CP_*"，結尾是 CP_ 用 "*CP_"，
    只要「包含」CP_（不論在任何位置）則前後都加 * 寫成 "*CP_*"。
    回傳符合的欄位名稱與前幾筆資料"""
    con = duckdb.connect(DATABASE, read_only=True)
    if table not in con.execute("SHOW TABLES").fetchdf()['name'].tolist():
        con.close()
        return f"找不到表格「{table}」"

    all_columns = con.execute(f'DESCRIBE "{table}"').fetchdf()['column_name'].tolist()
    matched = [c for c in all_columns if any(fnmatch.fnmatch(c, p) for p in columns)]
    if not matched:
        con.close()
        return f"表格「{table}」中沒有欄位符合「{columns}」"

    cols_sql = ", ".join(f'"{c}"' for c in matched)
    df = con.execute(f'SELECT {cols_sql} FROM "{table}" LIMIT 5').fetchdf()
    con.close()
    return f"符合的欄位：{matched}\n前 5 筆資料：\n{df.to_string(index=False)}"


@tool
def run_anova(table: str, x: str, y: list[str], top_n: int = 10) -> str:
    """對指定表格做單因子 ANOVA 分析。x 是分組欄位（類別型，例如 "Equipment"）。
    y 是要比較的數值欄位，每一項可以是精確欄位名稱，也可以用 * 做模糊比對（例如 "CP_*"），
    符合的欄位再多都可以，不用先展開列出來。
    如果符合的欄位很多，只會回傳最顯著的 top_n 筆摘要，完整結果會存成 csv 檔並回傳路徑"""
    con = duckdb.connect(DATABASE, read_only=True)
    if table not in con.execute("SHOW TABLES").fetchdf()['name'].tolist():
        con.close()
        return f"找不到表格「{table}」"

    all_columns = con.execute(f'DESCRIBE "{table}"').fetchdf()['column_name'].tolist()
    matched = [c for c in all_columns if any(fnmatch.fnmatch(c, p) for p in y)]
    if not matched:
        con.close()
        return f"表格「{table}」中沒有欄位符合「{y}」"

    cols_sql = ", ".join(f'"{c}"' for c in matched)
    df = con.execute(f'SELECT "{x}", {cols_sql} FROM "{table}"').df()
    con.close()

    rows = []
    for y_col in matched:
        groups = [g[y_col].dropna().values for _, g in df.groupby(x)]
        f_stat, p_value = scipy_stats.f_oneway(*groups)
        rows.append({"y": y_col, "f_statistic": round(float(f_stat), 4), "p_value": round(float(p_value), 4)})
    result_df = pd.DataFrame(rows).sort_values("p_value")

    Path(RESULTS_DIR).mkdir(parents=True, exist_ok=True)
    result_path = f"{RESULTS_DIR}/anova_{table}_{x}.csv"
    result_df.to_csv(result_path, index=False)

    n_significant = int((result_df["p_value"] < 0.05).sum())
    top = result_df.head(top_n)
    lines = [
        f"共檢定 {len(result_df)} 個欄位，{n_significant} 個顯著（p<0.05）",
        f"完整結果已存到：{result_path}",
        f"最顯著的前 {len(top)} 個：",
    ]
    for _, row in top.iterrows():
        lines.append(f"- {row['y']}: F={row['f_statistic']}, p={row['p_value']}")
    return "\n".join(lines)


tools = [select_columns, run_anova]
model = getModel().bind_tools(tools)


def human_node(state: State) -> dict:
    user_input = interrupt("用戶輸入")
    return {"messages": [HumanMessage(user_input)]}


def agent_node(state: State) -> dict:
    return {"messages": [model.invoke(state['messages'])]}


builder = StateGraph(State)
builder.add_node("human", human_node)
builder.add_node("agent", agent_node)
builder.add_node("tools", ToolNode(tools))

builder.add_edge(START, "human")
builder.add_edge("human", "agent")
builder.add_conditional_edges("agent", tools_condition, {
    "tools": "tools",
    END: END,
})
builder.add_edge("tools", "agent")

graph = builder.compile(checkpointer=MemorySaver())


if __name__ == '__main__':
    thread_id = uuid4().hex[:4]
    config = {"configurable": {"thread_id": thread_id}}
    state = State(
        messages=[
            SystemMessage(
                '你有一張表格 tab ，'
            )        
        ], 
        intent={}
    )
    graph.invoke(state, config=config)
    result = graph.invoke(Command(resume="我需要 tab 將包含 CP_ 的欄位都挑出來"), config=config)
    for msg in result['messages']:
        print(f"[{type(msg).__name__}] {msg.content}")
