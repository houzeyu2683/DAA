import os
import json
import re
import duckdb
import dotenv
from typing import Annotated, TypedDict

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, InjectedState

_ = dotenv.load_dotenv()


class State(TypedDict):
    messages: list
    database: str
    table_name: str
    columns_source: str
    anova_source: str


def get_columns(
    table_name: str,
    state: Annotated[dict, InjectedState],
) -> str:
    """查詢資料表的所有欄位，結果存檔，回傳摘要。"""
    database = state["database"]
    con = duckdb.connect(database, read_only=True)
    rows = con.execute(f"DESCRIBE {table_name}").fetchall()
    columns = [{"name": row[0], "type": row[1]} for row in rows]
    con.close()

    os.makedirs(".cache", exist_ok=True)
    source_path = f".cache/{table_name}_columns.json"
    json.dump(columns, open(source_path, "w"), ensure_ascii=False, indent=2)

    names = [c["name"] for c in columns]
    preview = ", ".join(names[:6] + names[-6:]) if len(names) > 12 else ", ".join(names)
    return json.dumps({
        "columns_description": f"Table '{table_name}' has {len(names)} columns: {preview}. Full details at {source_path}.",
        "columns_source": source_path,
    })


def filter_columns(
    pattern: str,
    state: Annotated[dict, InjectedState],
) -> str:
    """用 regex 篩選欄位，結果存檔，回傳摘要。"""
    columns = json.load(open(state["columns_source"]))
    matched = [c for c in columns if re.search(pattern, c["name"])]

    source_path = ".cache/filtered_columns.json"
    json.dump(matched, open(source_path, "w"), ensure_ascii=False, indent=2)

    names = [c["name"] for c in matched]
    preview = ", ".join(names[:6] + names[-6:]) if len(names) > 12 else ", ".join(names)
    return json.dumps({
        "columns_description": f"Pattern '{pattern}' matched {len(names)} columns: {preview}. Full details at {source_path}.",
        "columns_source": source_path,
    })


def run_anova(
    group_col: str,
    state: Annotated[dict, InjectedState],
) -> str:
    """對篩選後的欄位跑 ANOVA，結果排序後存檔，回傳前五名。"""
    from scipy import stats

    database = state["database"]
    columns = json.load(open(state["columns_source"]))
    col_names = [c["name"] for c in columns]

    con = duckdb.connect(database, read_only=True)
    table_name = state["table_name"]
    df = con.execute(f"SELECT * FROM {table_name}").df()
    con.close()

    results = []
    for col in col_names:
        if col == group_col:
            continue
        groups = [group[col].dropna().values for _, group in df.groupby(group_col)]
        if len(groups) < 2:
            continue
        f_stat, p_value = stats.f_oneway(*groups)
        results.append({"column": col, "f_stat": round(f_stat, 4), "p_value": round(p_value, 6)})

    results.sort(key=lambda x: x["f_stat"], reverse=True)

    source_path = ".cache/anova_results.json"
    json.dump(results, open(source_path, "w"), ensure_ascii=False, indent=2)

    top5 = results[:5]
    return json.dumps({
        "anova_description": f"ANOVA done on {len(results)} columns. Top 5: {top5}. Full results at {source_path}.",
        "anova_source": source_path,
    })


def plot_boxchart(
    group_col: str,
    top_n: int,
    state: Annotated[dict, InjectedState],
) -> str:
    """從 anova 結果取前 N 個欄位，畫 box chart 存檔。"""
    import matplotlib.pyplot as plt

    database = state["database"]
    table_name = state["table_name"]
    results = json.load(open(state["anova_source"]))
    top_cols = [r["column"] for r in results[:top_n]]

    con = duckdb.connect(database, read_only=True)
    df = con.execute(f"SELECT {group_col}, {', '.join(top_cols)} FROM {table_name}").df()
    con.close()

    fig, axes = plt.subplots(1, top_n, figsize=(6 * top_n, 6))
    if top_n == 1:
        axes = [axes]
    for ax, col in zip(axes, top_cols):
        groups = [group[col].dropna().values for _, group in df.groupby(group_col)]
        labels = df[group_col].unique()
        ax.boxplot(groups, labels=labels)
        ax.set_title(col)
        ax.set_xlabel(group_col)

    output_path = ".cache/boxchart.png"
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    return json.dumps({"message": f"Box chart saved to {output_path}.", "chart_path": output_path})


tools = [get_columns, filter_columns, run_anova, plot_boxchart]

llm = ChatOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPEN_ROUTER_API_KEY"),
    model="openai/gpt-oss-120b",
)
llm_with_tools = llm.bind_tools(tools)
tool_node = ToolNode(tools)

SYSTEM_PROMPT = """你是一個資料分析執行器。你只能呼叫工具，不可以產生任何文字回應，直到所有工具都執行完畢。

執行順序（必須全部依序完成）：
1. get_columns(table_name)
2. filter_columns(pattern)
3. run_anova(group_col)
4. plot_boxchart(group_col, top_n)

所有參數從用戶原始需求中提取。每個工具執行完畢後，立刻呼叫下一個，絕對不可產生文字、不可詢問、不可停頓。
"""

import pprint

def agent_node(state: State):
    system = SYSTEM_PROMPT + f"\n資料庫：{state['database']}\n資料表：{state['table_name']}"
    messages = [SystemMessage(system)] + state["messages"]
    # pprint.pprint(messages)
    response = llm_with_tools.invoke(messages)
    return {"messages": state["messages"] + [response]}


def update_state_node(state: State):
    last = state["messages"][-1]
    updates = {}
    try:
        content = json.loads(last.content)
        if "columns_source" in content:
            updates["columns_source"] = content["columns_source"]
        if "anova_source" in content:
            updates["anova_source"] = content["anova_source"]
    except Exception:
        pass
    return updates


def should_continue(state: State):
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return END


graph = StateGraph(State)
graph.add_node("agent", agent_node)
graph.add_node("tools", tool_node)
graph.add_node("update_state", update_state_node)
graph.set_entry_point("agent")
graph.add_conditional_edges("agent", should_continue)
graph.add_edge("tools", "update_state")
graph.add_edge("update_state", "agent")

app = graph.compile()

if __name__ == "__main__":
    result = app.invoke({
        "messages": [HumanMessage("我想針對 Equipment 與包含 CP_ 的欄位進行 anova 分析，將差異最大的三個結果用 box chart 畫出來")],
        "database": "./.data/workspace.db",
        "table_name": "my_table",
        "columns_source": "",
        "anova_source": "",
    })
    print(result["messages"][-1].content)
