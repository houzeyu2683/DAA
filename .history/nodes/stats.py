from core.status import State
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from typing import TypedDict, Literal, List
import duckdb
from core.functions import getModel
from langchain_core.messages import filter_messages
import pandas as pd
from scipy import stats

class StatsPlan(TypedDict):
    method: Literal["anova", "ttest", "correlation", "chi2"]
    x: List[str]
    y: List[str]
    explanation: str

model = getModel()
_planner = model.with_structured_output(StatsPlan)

def stats_node(state: State, config: RunnableConfig) -> dict:
    table = state["tables"][-1]
    database = config["configurable"]['database']

    con = duckdb.connect(database, read_only=True)
    df = con.execute(f"SELECT * FROM {table['name']}").df()
    con.close()

    columns = df.columns.tolist()

    system = SystemMessage(content=f"""你是一個統計分析規劃器。

可用欄位：
{columns}

支援的分析方法：
- anova：單因子變異數分析，x 為類別欄位（分組），y 為數值欄位（可多個）
- ttest：獨立樣本 t 檢定，x 為兩組類別，y 為一個數值欄位
- correlation：相關係數分析，不需要 x，y 為多個數值欄位
- chi2：卡方檢定，x 和 y 都是類別欄位

根據任務選擇適合的方法，並從可用欄位中選出對應的 x 和 y。
""")

    task = state['tasks'][0]
    conversation = filter_messages(state["messages"], include_types=["human", "ai"])

    res = _planner.invoke([system] + conversation[-4:] + [HumanMessage(task['description'])])
    if res["method"] == "anova":
        result = run_anova(df, res["x"], res["y"])
    elif res["method"] == "ttest":
        result = run_ttest(df, res["x"], res["y"])
    elif res["method"] == "correlation":
        result = run_correlation(df, res["y"])
    elif res["method"] == "chi2":
        result = run_chi2(df, res["x"], res["y"])

    return {
        "tasks": state["tasks"][1:],
        "stats": [{"method": res["method"], "summary": res["explanation"], "data": result}],
        "messages": [AIMessage(content=f"[統計] {res['explanation']}")]
    }


def run_anova(df: pd.DataFrame, x: list[str], y: list[str]) -> dict:
    
    x_col = x[0]
    results = []
    for y_col in y:
        groups = [group[y_col].dropna().values for _, group in df.groupby(x_col)]
        f_stat, p_value = stats.f_oneway(*groups)
        group_means = df.groupby(x_col)[y_col].mean().sort_values(ascending=False)
        results.append({
            "y": y_col,
            "f_statistic": round(float(f_stat), 4),
            "p_value": round(float(p_value), 4),
            "significant": p_value < 0.05,
            "group_means": {str(k): round(float(v), 4) for k, v in group_means.items()}
        })
    return {"method": "anova", "x": x_col, "results": results}

def run_ttest(df: pd.DataFrame, x: list[str], y: list[str]) -> dict:
    return {
    }

def run_correlation(df: pd.DataFrame, x: list[str], y: list[str]) -> dict:
    return {"method": "correlation"}

def run_chi2(df, x: list[str], y: list[str]) -> dict:
    return {"method": "chi2", "result": "假結果"}