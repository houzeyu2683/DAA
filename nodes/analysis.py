import os
from typing import Optional

import duckdb
import pandas as pd
from dotenv import load_dotenv
from scipy import stats
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_openai import ChatOpenAI

from nodes.coordination import CoordinationState
from tools.default import (
    check_table_exist,
    create_table,
    get_table_shape,
    get_columns_type,
    get_columns_type_distribution,
    list_columns,
    preview_table,
)

load_dotenv()
MODEL_NAME = os.environ["MODEL_NAME"]
MODEL_URL = os.environ["MODEL_URL"]
API_KEY = os.environ["API_KEY"]


model = ChatOpenAI(
    model=MODEL_NAME,
    temperature=0,
    base_url=MODEL_URL,
    api_key=API_KEY,
)


def _resolve_cols(names: list, pattern: dict, all_cols: list) -> list:
    if names:
        return [c for c in names if c in all_cols]
    matched = []
    for p, mode in (pattern or {}).items():
        if mode == "contains":
            matched += [c for c in all_cols if p in c]
        elif mode == "startwith":
            matched += [c for c in all_cols if c.startswith(p)]
        elif mode == "endwith":
            matched += [c for c in all_cols if c.endswith(p)]
    return [c for i, c in enumerate(matched) if c not in matched[:i]]


def _resolve_tag(names: list, pattern: dict) -> str:
    if names:
        return '_'.join(names)
    return "_".join([k for k in (pattern or {})])


@tool
def run_ANOVA_with_categories_and_numerics(
    database_path: str,
    table_name: str,
    categories: Optional[list] = None,
    categories_pattern: Optional[dict] = None,
    numerics: Optional[list] = None,
    numerics_pattern: Optional[dict] = None,
) -> dict:
    """對類別欄位與數值欄位做單因子 ANOVA。
    categories/numerics 各自可以是一個或多個欄位，用 list 明確列出欄位名稱。

    如果欄位數量很多、無法一一列舉(例如所有包含某個字串的欄位)，
    改用 cats_pattern/nums_pattern 比對欄位名稱，格式是 {pattern字串: 比對方式}，
    比對方式可以是 "contains"(包含)、"startwith"(開頭是)、"endwith"(結尾是)。

    categories 與 categories_pattern 必須只能擇一輸入；numerics 與 nums_pattern 也是只能擇一輸入。

    內部會對「類別欄位 x 數值欄位」的每一種組合各跑一次 ANOVA，
    完整結果存入資料庫的一張新表，回傳依 p_value 排序後的截斷預覽文字。

    參數:
        database_path: DuckDB 資料庫檔案的路徑。
        table_name: 要分析的資料表名稱。
        categories: 類別欄位名稱清單。
        categories_pattern: 類別欄位的比對規則。
        numerics: 數值欄位名稱清單。
        numerics_pattern: 數值欄位的比對規則。
    """
    con = duckdb.connect(database_path, read_only=True)
    try:
        all_cols = [row[0] for row in con.execute(f"DESCRIBE {table_name}").fetchall()]

        cat_cols = _resolve_cols(categories, categories_pattern, all_cols)
        num_cols = _resolve_cols(numerics, numerics_pattern, all_cols)

        results = []
        for cat in cat_cols:
            for num in num_cols:
                df = con.execute(f"SELECT {cat}, {num} FROM {table_name}").df()
                groups = [g[num].dropna() for _, g in df.groupby(cat) if len(g) > 0]
                if len(groups) < 2:
                    continue
                f_stat, p_value = stats.f_oneway(*groups)
                results.append({
                    "table_name": table_name,
                    "cat": cat,
                    "num": num,
                    "n_groups": len(groups),
                    "f_stat": f_stat,
                    "p_value": p_value,
                })
    finally:
        con.close()

    if not results:
        return "沒有找到符合條件的類別欄位與數值欄位組合，未執行任何 ANOVA。"

    results_df = pd.DataFrame(results).sort_values("p_value")
    tag = _resolve_tag(numerics, numerics_pattern) + "_" + _resolve_tag(categories, categories_pattern)
    stats_table_name = f"{table_name}_anova_{tag}"
    create_table.invoke({
        "database_path": database_path,
        "table_name": stats_table_name,
        "table_content": results_df,
    })

    preview = results_df.to_string(max_rows=10, max_cols=10, show_dimensions=False)
    return {"stats_table_name": stats_table_name, "stats_table_preview": preview}


tools = [
    check_table_exist,
    get_table_shape,
    get_columns_type,
    get_columns_type_distribution,
    list_columns,
    preview_table,
    run_ANOVA_with_categories_and_numerics,
]

ANALYSIS_NODE_PROMPT = (
    "你是統計分析專家，負責針對已經存在於 DuckDB 資料庫中的表，"
    "回答與資料統計相關的問題，例如表格與欄位有哪些、欄位的型別、"
    "以及類別欄位與數值欄位之間的 ANOVA 分析。"
    "你只能以唯讀方式查詢原始資料，絕對不能新增、修改或刪除原始資料表的任何資料。"
    "禁止產生任何程式碼，"
    "在呼叫工具、拿到工具實際回傳的結果之前，絕對不能寫出任何看起來像統計數字、"
    "表格或分析結論的內容(不能自己編數字)，只能根據工具真正回傳的資料來描述結果，"
    "完成任務後總結一下做了什麼，有哪些關鍵資訊(例如統計結果表名)？"
)

analysis_agent = create_agent(
    model,
    tools=tools,
    system_prompt=ANALYSIS_NODE_PROMPT,
)


def analysis_node(state: CoordinationState) -> dict:
    messages = state['messages']
    response = analysis_agent.invoke({"messages": messages})

    for message in response['messages']:
        message.pretty_print()

    update = {"messages": response["messages"][1:]}
    return update
