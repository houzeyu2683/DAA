import os
import duckdb
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
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


@tool
def read_stats(db_path: str, stats_tb_name: str, top_n: int) -> dict:
    """查看差異最大的前 n 筆統計數據(依 p_value 由小到大排序，p_value 越小代表差異越顯著)。

    參數:
        db_path: DuckDB 資料庫檔案的路徑。
        stats_tb_name: 統計結果表名稱(例如 anova_with_cats_and_nums 產生的表)。
        top_n: 要看前幾筆。
    """
    con = duckdb.connect(db_path, read_only=True)
    try:
        df = con.execute(
            f"SELECT * FROM {stats_tb_name} ORDER BY p_value ASC LIMIT {int(top_n)}"
        ).df()
    finally:
        con.close()

    if df.empty:
        return f"表 {stats_tb_name} 沒有資料。"

    # preview = df.to_string(max_rows=int(top_n), max_cols=10, show_dimensions=False)
    # return f"依 p_value 由小到大排序的前 {len(df)} 筆統計結果：\n{preview}"
    overview = df.to_string()
    return {
        'overview': overview
    }


@tool
def plot_box_chart(db_path: str, tb_name: str, cat: str, num: str) -> str:
    """對指定表裡的類別欄位(cat)與數值欄位(num)畫箱型圖(box chart)，
    圖片存成 PNG 檔案，回傳檔案路徑與簡短說明文字。

    參數:
        db_path: DuckDB 資料庫檔案的路徑。
        tb_name: 資料表名稱(需為含有逐筆資料的原始表，不能是統計結果表)。
        cat: 類別欄位名稱(分組依據，畫在 x 軸)。
        num: 數值欄位名稱(要畫分布的對象，畫在 y 軸)。
    """
    con = duckdb.connect(db_path, read_only=True)
    try:
        all_cols = [row[0] for row in con.execute(f"DESCRIBE {tb_name}").fetchall()]
        if cat not in all_cols or num not in all_cols:
            return f"欄位 {cat} 或 {num} 不存在於表 {tb_name} 中，未畫圖。"

        df = con.execute(f"SELECT {cat}, {num} FROM {tb_name}").df()
    finally:
        con.close()

    groups = {name: g[num].dropna() for name, g in df.groupby(cat) if len(g) > 0}
    if len(groups) < 2:
        return f"欄位 {cat} 的分組數量不足，未畫圖。"

    fig, ax = plt.subplots()
    ax.boxplot(groups.values(), labels=groups.keys())
    ax.set_xlabel(cat)
    ax.set_ylabel(num)
    ax.set_title(f"{num} by {cat}")
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    fig.tight_layout()

    save_path = os.path.abspath(f"{tb_name}_{cat}_{num}_boxplot.png")
    fig.savefig(save_path)
    plt.close(fig)

    return f"已將 {cat} x {num} 的箱型圖存成圖檔，路徑：{save_path}"



model = ChatOpenAI(
    model=MODEL_NAME,
    temperature=0,
    base_url=MODEL_URL,
    api_key=API_KEY
)
checkpointer = InMemorySaver()

CHART_AGENT_PROMPT = (
    "你是資料分析師，負責解讀統計數據，使用視覺化技術來對原始資料進行畫圖"
    "你的職責是將閱讀統計數據，根據用戶的問題來視覺化資料。"
)

tools = [read_stats, plot_box_chart]
chart_agent = create_agent(
    model,
    tools=tools,
    system_prompt=CHART_AGENT_PROMPT
)






config = {"configurable": {"thread_id": "666"}}
DB_PATH = ".data/tmp/data_agent_demo/database.db"
TB_NAME = "fifa_world_cup_2026_player_performance"
STATS_TABLE_NAME = "fifa_world_cup_2026_player_performance_anova_minutes_played__id"

question = (
    f"資料庫位於{DB_PATH}，先前已經將用戶 CSV 檔案紀錄到資料庫中，"
    f"表格名稱是{TB_NAME}，"
    f"統計結果是{STATS_TABLE_NAME}"
    f"幫我把差異最大的畫出 box chart"
)


if __name__ == "__main__":
    result = chart_agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
        config,
    )
    for message in result["messages"]:
        message.pretty_print()
