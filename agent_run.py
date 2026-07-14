"""
不經過 MCP,把之前在 mcp-server/data.py、mcp-server/stats.py 裡驗證過的工具邏輯,
直接搬進同一個 Python process,用最單純的 @tool 建立 agent。

目的:先把「agent 邏輯」(docstring、supervisor 隔離、依序/平行)搞清楚、跑穩,
之後要不要把某個工具重新包成 MCP server,是後面獨立的一步,不影響這裡的邏輯。

架構:
- main_agent:只看得到 get_schema、load_table,以及一個「委派給統計專家」的工具。
- stats_agent:只看得到 anova_by_pattern,main_agent 看不到它。
"""

import asyncio
import os
import re
import uuid
from collections import Counter
from pathlib import Path
from typing import Literal

import duckdb
import pandas as pd
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from scipy import stats as scipy_stats

load_dotenv()

MODEL_URL = os.environ["MODEL_URL"]
API_KEY = os.environ["API_KEY"]
MODEL_NAME = os.environ["MODEL_NAME"]

DATABASE_PATH = ".data/tmp/database.db"

DATABASE_PROMPT = (
    "這次對話已經分配了一個專屬的工作空間,"
    f"裡面的 DuckDB 資料庫路徑是:{DATABASE_PATH}。\n"
    "凡是工具需要 database_path 這個參數時,一律使用這個路徑,"
    "不要自己猜測或編造其他路徑。"
)


# ============================================================
# 資料相關:搬自 mcp-server/data.py
# ============================================================

def _get_schema(database_path: str, table_name: str) -> dict:
    con = duckdb.connect(database_path, read_only=True)
    try:
        description = con.execute(f"DESCRIBE {table_name}").fetchall()
        con.close()
    except Exception as e:
        con.close()
        raise Exception(f"_get_schema 執行錯誤: {e}")

    cols = [{"name": col[0], "type": col[1]} for col in description]
    total = len(description)
    types = dict(Counter(col[1] for col in description))
    return {"cols": cols, "total": total, "types": types}


@tool
def get_schema(database_path: str, table_name: str) -> dict:
    """
    查詢指定資料表的 schema(欄位資訊)。

    參數:
        database_path: DuckDB 資料庫檔案的路徑。
        table_name: 要查詢的資料表名稱。

    回傳一個 dict,包含:
        - cols: 欄位清單(每個元素含 name、type),最多只回傳前 16 個欄位。
        - total: 該表實際的總欄位數。
        - types: 各型別出現的次數統計,例如 {"VARCHAR": 7, "BIGINT": 32}。
        - truncated: bool,
            - True 代表 cols 只是部分欄位的預覽(total > 16 時被截斷)
            - False 代表 cols 就是完整清單。
    """
    head = 16
    try:
        schema = _get_schema(database_path, table_name)
    except Exception as e:
        raise Exception(f"get_schema 執行錯誤: {e}")

    if schema["total"] > head:
        schema["cols"] = schema["cols"][:head]
        schema["truncated"] = True
    else:
        schema["truncated"] = False

    return schema


def _make_table_name(filename: str) -> str:
    name = filename.rsplit(".", 1)[0].lower()
    name = re.sub(r"[^a-z0-9_]", "_", name)
    name = name.strip("_") or "table"
    suffix = uuid.uuid4().hex[:6]
    return f"raw_{name}_{suffix}"


@tool
def load_table(table_path: str, database_path: str) -> dict:
    """讀取一份 CSV 檔案,寫入指定的 DuckDB 資料庫,成為一張新的表。

    表名會根據原始檔名自動產生(轉小寫、非英數字元換成底線),
    並附加一段隨機碼避免重名衝突,例如 sales-2024.csv
    會建成類似 raw_sales_2024_a3f9c2 這樣的表名。

    參數:
        table_path: CSV 檔案的路徑。
        database_path: 要寫入的 DuckDB 資料庫檔案路徑。

    回傳一個 dict,包含:
        - table_name: 實際建立的表名。
        - csv_filename: 使用者原始的檔名,方便之後對照。
        - nrow: 這張表寫入的資料筆數。
    """
    csv_filename = os.path.basename(table_path)
    table_name = _make_table_name(csv_filename)

    try:
        df = pd.read_csv(table_path)
    except Exception as e:
        raise Exception(f"load_table 讀取 CSV 失敗: {e}")

    Path(database_path).parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(database_path)
    try:
        con.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM df")
        con.close()
    except Exception as e:
        con.close()
        raise Exception(f"load_table 寫入資料庫失敗: {e}")

    return {
        "table_name": table_name,
        "csv_filename": csv_filename,
        "nrow": len(df),
    }


# ============================================================
# 統計相關:搬自 mcp-server/stats.py
# ============================================================

MATCH_TYPES = ("contains", "startswith", "endswith")


def _find_cols_with_pattern(
    database_path: str,
    table_name: str,
    pattern: str,
    match_type: Literal["contains", "startswith", "endswith"],
) -> list[str]:
    sql_pattern = {
        "contains": f"%{pattern}%",
        "startswith": f"{pattern}%",
        "endswith": f"%{pattern}",
    }[match_type]

    con = duckdb.connect(database_path, read_only=True)
    try:
        rows = con.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = ? AND column_name LIKE ?",
            [table_name, sql_pattern],
        ).fetchall()
    finally:
        con.close()

    return [row[0] for row in rows]


def _run_anova(database_path: str, table_name: str, group_column: str, value_columns: list[str]) -> list[dict]:
    if not value_columns:
        return []

    columns_sql = ", ".join(f'"{c}"' for c in [group_column, *value_columns])
    con = duckdb.connect(database_path, read_only=True)
    try:
        df = con.execute(f"SELECT {columns_sql} FROM {table_name}").fetchdf()
    finally:
        con.close()

    results = []
    for column in value_columns:
        if not pd.api.types.is_numeric_dtype(df[column]):
            results.append({"column": column, "error": "非數值欄位,無法做 ANOVA"})
            continue

        groups = [
            group_df[column].dropna().to_numpy()
            for _, group_df in df[[group_column, column]].dropna().groupby(group_column)
        ]
        groups = [g for g in groups if len(g) >= 2]

        if len(groups) < 2:
            results.append({"column": column, "error": "有效分組數不足(需要至少 2 組,每組至少 2 筆資料),無法做 ANOVA"})
            continue

        f_stat, p_value = scipy_stats.f_oneway(*groups)
        results.append({"column": column, "f_stat": float(f_stat), "p_value": float(p_value)})

    return results


def _summarize(results: list[dict], head: int = 20) -> dict:
    valid = sorted((r for r in results if "p_value" in r), key=lambda r: r["p_value"])
    errors = [r for r in results if "error" in r]

    return {
        "total_tested": len(results),
        "valid_count": len(valid),
        "skipped_count": len(errors),
        "results": valid[:head],
        "skipped": errors[:head],
        "truncated": len(valid) > head,
    }


def _save_results(database_path: str, results: list[dict]) -> str | None:
    valid = [r for r in results if "p_value" in r]
    if not valid:
        return None

    results_df = pd.DataFrame(valid)
    table_name = f"stats_anova_{uuid.uuid4().hex[:6]}"

    con = duckdb.connect(database_path)
    try:
        con.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM results_df")
    finally:
        con.close()

    return table_name


@tool
def anova_by_pattern(
    database_path: str,
    table_name: str,
    group_column: str,
    pattern: str,
    match_type: str,
) -> dict:
    """對指定資料表中,欄位名稱符合命名規則的所有數值欄位,
    各自對 group_column 做單因子 ANOVA(one-way ANOVA)。

    參數:
        database_path: DuckDB 資料庫檔案的路徑。
        table_name: 要分析的資料表名稱。
        group_column: 分組欄位(類別型),ANOVA 用來分組比較的依據。
        pattern: 欄位名稱比對的字串。
        match_type: 比對規則,必須是 "contains"、"startswith"、"endswith" 之一。

    回傳一個 dict,包含:
        - stats_name: 完整統計結果所在的表名,可再對它下 SQL 查詢。若無有效結果則為 None。
        - total_tested: 實際被嘗試分析的欄位總數。
        - valid_count: 成功算出 ANOVA 結果的欄位數。
        - skipped_count: 被跳過的欄位數。
        - results: 依 p_value 由小到大排序的結果清單,最多 20 筆。
        - skipped: 被跳過欄位的清單,最多 20 筆。
        - truncated: bool,True 代表 results 只是部分結果。
    """
    if match_type not in MATCH_TYPES:
        raise Exception(f"anova_by_pattern 錯誤: match_type 必須是 {MATCH_TYPES} 之一")

    try:
        value_columns = _find_cols_with_pattern(database_path, table_name, pattern, match_type)
        results = _run_anova(database_path, table_name, group_column, value_columns)
        stats_name = _save_results(database_path, results)
    except Exception as e:
        raise Exception(f"anova_by_pattern 執行錯誤: {e}")

    summary = _summarize(results)
    summary["stats_name"] = stats_name
    return summary


# ============================================================
# Agent 架構:主 agent + 統計子 agent
# ============================================================

model = ChatOpenAI(model=MODEL_NAME, base_url=MODEL_URL, api_key=API_KEY)

STATS_SYSTEM_PROMPT = "你是統計分析專家,根據使用者需求選擇合適的統計方法並執行。" + DATABASE_PROMPT
stats_agent = create_agent(model, tools=[anova_by_pattern], system_prompt=STATS_SYSTEM_PROMPT)


@tool
async def run_statistical_analysis(request: str) -> str:
    """當使用者的需求涉及統計分析(例如變異數分析、相關係數、假設檢定等)時,
    呼叫這個工具。request 裡務必包含:要分析的表名(table_name)、
    想比較/分組的欄位、以及使用者想知道什麼,用自然語言描述清楚,
    交給專門的統計分析專家處理。"""
    result = await stats_agent.ainvoke({"messages": [{"role": "user", "content": request}]})
    return result["messages"][-1].content


MAIN_SYSTEM_PROMPT = "你是一個資料分析助理。" + DATABASE_PROMPT
main_agent = create_agent(
    model,
    tools=[get_schema, load_table, run_statistical_analysis],
    system_prompt=MAIN_SYSTEM_PROMPT,
)


async def main() -> None:
    question = (
        "幫我讀取 '.data/archive/fifa_world_cup_2026_player_performance.csv',"
        "然後幫我看看球員的 position(位置)分組之下,"
        "所有欄位名稱包含 'goals' 的數值欄位,是否有顯著差異。"
    )
    result = await main_agent.ainvoke({"messages": [{"role": "user", "content": question}]})

    for message in result["messages"]:
        message.pretty_print()


if __name__ == "__main__":
    asyncio.run(main())
