import os
import duckdb
import pandas as pd
from dotenv import load_dotenv
from scipy import stats
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langgraph.checkpoint.memory import InMemorySaver


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


def _check_tb_exist(db_path: str, tb_name: str) -> bool:
    '''檢查資料庫中的表是否存在'''
    con = duckdb.connect(db_path, read_only=True)
    try:
        tb_names = [row[0] for row in con.execute("SHOW TABLES").fetchall()]
    finally:
        con.close()
    return tb_name in tb_names


def _insert_tb(stats_res: dict, tb_name: str, db_path: str) -> bool:
    """將轉換成表格的統計結果寫入指定的 DB 資料庫"""
    # tb_name = stats_result['stats_name']
    stats_df = pd.DataFrame([stats_res])
    
    con = duckdb.connect(db_path)
    try:
        con.execute(
            f"CREATE OR REPLACE TABLE {tb_name} AS SELECT * FROM stats_df"
        )
        _ = stats_df
    finally:
        con.close()
    
    return True


def _select_cols_with_names(db_path: str, tb_name: str, cols_names: list) -> pd.DataFrame:
    """從資料庫中的表挑選欄位"""
    cols = ", ".join(cols_names)
    con = duckdb.connect(db_path, read_only=True)
    try:
        df = con.execute(f"SELECT {cols} FROM {tb_name}").df()
    finally:
        con.close()
    return df


def _select_cols_with_pattern(db_path: str, tb_name: str, cols_pattern: str, pattern_mode: str = "contains") -> pd.DataFrame:
    """從資料庫中的表挑選欄位名稱符合特定模式的欄位。
    pattern_mode 可以是 "contains"(包含)、"startswith"(開頭)、"endswith"(結尾)"""
    con = duckdb.connect(db_path, read_only=True)
    try:
        col_names = [row[0] for row in con.execute(f"DESCRIBE {tb_name}").fetchall()]
        if pattern_mode == "contains":
            matched = [c for c in col_names if cols_pattern in c]
        elif pattern_mode == "startswith":
            matched = [c for c in col_names if c.startswith(cols_pattern)]
        elif pattern_mode == "endswith":
            matched = [c for c in col_names if c.endswith(cols_pattern)]
        else:
            matched = []
        cols = ", ".join(matched)
        df = con.execute(f"SELECT {cols} FROM {tb_name}").df()
    finally:
        con.close()
    return df


def _anova_with_cat_and_num(tb_df: pd.DataFrame, cat_col: str, num_col: str) -> dict:
    """對 tb_df 裡的類別欄位(cat_col)與數值欄位(num_col)做單因子 ANOVA，
    回傳 F 統計量與 p-value(p-value 越小，代表各組平均值差異越顯著)"""
    groups = [
        group[num_col].dropna()
        for _, group in tb_df.groupby(cat_col)
        if len(group) > 0
    ]
    f_stat, p_value = stats.f_oneway(*groups)
    stats_name = f'anova_with_{cat_col}_and_{num_col}'
    return {
        'stats_name': stats_name,
        "cat_col": cat_col,
        "num_col": num_col,
        "n_groups": len(groups),
        "f_stat": f_stat,
        "p_value": p_value,
    }


@tool
def anova_with_cat_and_num(db_path: str, tb_name: str, cat_col: str, num_col: str) -> dict:
    """對指定表裡的一個類別欄位與一個數值欄位做單因子 ANOVA，
    回傳 F 統計量與 p-value，p-value 越小代表各組平均值差異越顯著。

    參數:
        db_path: DuckDB 資料庫檔案的路徑。
        tb_name: 資料表名稱。
        cat_col: 類別欄位名稱(分組依據)。
        num_col: 數值欄位名稱(要比較的對象)。
    """
    df = _select_cols_with_names(db_path, tb_name, [cat_col, num_col])
    stats_res = _anova_with_cat_and_num(df, cat_col, num_col)
    _ =_insert_tb(stats_res, stats_res['stats_name'], db_path)
    return stats_res


tools = [anova_with_cat_and_num]
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
CSV_PATH = ".data/archive/fifa_world_cup_2026_player_performance.csv"
DB_PATH = ".data/tmp/data_agent_demo/database.db"
TB_NAME = "fifa_world_cup_2026_player_performance"

question = (
    f"已經讀取{CSV_PATH}表格，並保存在資料庫資料庫在{DB_PATH}，"
    f"表格名稱是{TB_NAME}，"
    f"我要針對欄位'minutes_played'以及欄位'nationality', 'position'進行分析"
)


if __name__ == "__main__":
    result = stats_agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
        config,
    )
    for message in result["messages"]:
        message.pretty_print()
