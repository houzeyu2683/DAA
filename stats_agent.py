import os
import duckdb
import pandas as pd
from dotenv import load_dotenv
from scipy import stats
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from typing import Literal, Optional

load_dotenv()
MODEL_NAME = os.environ["MODEL_NAME"]
MODEL_URL = os.environ["MODEL_URL"]
API_KEY = os.environ["API_KEY"]


model = ChatOpenAI(
    model=MODEL_NAME,
    temperature=0,
    base_url=MODEL_URL,
    api_key=API_KEY
)
checkpointer = InMemorySaver()


def _save_stats_result_to_db(
    stats_result: pd.DataFrame, 
    stats_tb_name: str, 
    db_path: str
) -> bool:
    """將統計結果轉換成表格的寫入資料庫"""

    con = duckdb.connect(db_path)
    try:
        con.register("stats_result_view", stats_result)
        con.execute(
            f"CREATE OR REPLACE TABLE {stats_tb_name} AS SELECT * FROM stats_result_view"
        )
    finally:
        con.close()

    return True


def _resolve_cols(names: list, pattern: dict, all_cols: list) -> list:
    if names:
        return [c for c in names if c in all_cols]
    matched = []
    for p, mode in (pattern or {}).items():
        if mode == "contains":
            matched += [c for c in all_cols if p in c]
        elif mode == "startswith":
            matched += [c for c in all_cols if c.startswith(p)]
        elif mode == "endswith":
            matched += [c for c in all_cols if c.endswith(p)]
    return [c for i, c in enumerate(matched) if c not in matched[:i]]


def _resolve_tag(names: list, pattern: dict) -> str:
    if names:
        return '_'.join(names)
    return "_".join([k for k in pattern])


@tool
def anova_with_cats_and_nums(
    db_path: str,
    tb_name: str,
    cats: Optional[list] = None,
    cats_pattern: Optional[dict] = None,
    nums: Optional[list] = None,
    nums_pattern: Optional[dict] = None,
) -> dict:
    """對類別欄位與數值欄位做單因子 ANOVA。
    cats/nums 各自可以是一個或多個欄位，用 list 明確列出欄位名稱。

    如果欄位數量很多、無法一一列舉(例如所有包含某個字串的欄位)，
    改用 cats_pattern/nums_pattern 比對欄位名稱，格式是 {pattern字串: 比對方式}，
    可以同時給多組規則，例如:
        {"_device": "contains", "sensor_": "startswith"}
    代表「欄位名稱包含 _device」或「欄位名稱開頭是 sensor_」都算符合。
    比對方式(比對方式的值)可以是 "contains"(包含)、"startswith"(開頭是)、"endswith"(結尾是)。

    cats 與 cats_pattern 必須只能擇一輸入；nums 與 nums_pattern 也是只能擇一輸入。

    內部會對「類別欄位 x 數值欄位」的每一種組合各跑一次 ANOVA。
    完整結果存入資料庫的一張表，回傳依 p_value 排序後的截斷預覽文字。
    """
    con = duckdb.connect(db_path, read_only=True)
    try:
        all_cols = [row[0] for row in con.execute(f"DESCRIBE {tb_name}").fetchall()]

        cat_cols = _resolve_cols(cats, cats_pattern, all_cols)
        num_cols = _resolve_cols(nums, nums_pattern, all_cols)

        results = []
        for cat in cat_cols:
            for num in num_cols:
                df = con.execute(f"SELECT {cat}, {num} FROM {tb_name}").df()
                groups = [g[num].dropna() for _, g in df.groupby(cat) if len(g) > 0]
                if len(groups) < 2:
                    continue
                f_stat, p_value = stats.f_oneway(*groups)
                results.append({
                    "tb_name": tb_name,
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
    

    tag = _resolve_tag(nums, nums_pattern) + "_" + _resolve_tag(cats, cats_pattern)

    stats_tb_name = f"{tb_name}_anova_{tag}"
    _save_stats_result_to_db(results_df, stats_tb_name, db_path)

    preview = results_df.to_string(max_rows=10, max_cols=10, show_dimensions=False)
    return {
        'stats_tb_name': stats_tb_name,
        'stats_tb_preview': preview
    }



tools = [anova_with_cats_and_nums]
STATS_AGENT_PROMPT = (
    "你是統計分析專家，負責針對已經存在於 DuckDB 資料庫中的表，"
    "回答與資料統計相關的問題，例如表格與欄位有哪些、欄位的型別、"
    "缺失值與唯一值數量、數值欄位的分布(最小值、最大值、平均值、標準差)，"
    "以及文字欄位常見值的分佈。"
    "你只能以唯讀方式查詢資料，絕對不能新增、修改或刪除資料庫中的任何資料。"
    "禁止產生任何程式碼，"
    "完成任務後總結一下做了什麼，有哪些關鍵資訊？"
    "如果有保存"
    "以及接下來需要做什麼？"    
)
stats_agent = create_agent(
    model,
    tools=tools,
    system_prompt=STATS_AGENT_PROMPT,
    checkpointer=checkpointer
)


config = {"configurable": {"thread_id": "666"}}
DB_PATH = ".data/tmp/data_agent_demo/database.db"
TB_NAME = "fifa_world_cup_2026_player_performance"

question = (
    f"資料庫位於{DB_PATH}，先前已經將用戶 CSV 檔案紀錄到資料庫中，"
    f"表格名稱是{TB_NAME}，"
    f"接下來要針對欄位'minutes_played'以及欄位包含'_id'進行 ANOVA 分析"
)


if __name__ == "__main__":
    result = stats_agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
        config,
    )
    for message in result["messages"]:
        message.pretty_print()
