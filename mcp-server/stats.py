"""
專門用來處理統計的 MCP Tools Server
"""


import uuid

import duckdb
import pandas as pd
from mcp.server.fastmcp import FastMCP
from scipy import stats as scipy_stats
from typing import Literal

PORT = 8002
mcp = FastMCP(name="stats-server", host="0.0.0.0", port=PORT)

MATCH_TYPES = ("contains", "startswith", "endswith")


def _find_cols_with_pattern(
    database_path: str, 
    table_name: str, 
    pattern: str, 
    match_type: Literal['contains', 'startswith', 'endswith']
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

    cols = [row[0] for row in rows]
    return cols


def _run_anova(
    database_path: str, 
    table_name: str, 
    group_column: str, 
    value_columns: list[str]
) -> list[dict]:
    
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


@mcp.tool()
def anova_by_pattern(
    database_path: str,
    table_name: str,
    group_column: str,
    pattern: str,
    match_type: str,
) -> dict:
    """對指定資料表中,欄位名稱符合命名規則的所有數值欄位,
    各自對 group_column 做單因子 ANOVA(one-way ANOVA)。

    欄位篩選跟統計計算都在伺服器內部完成,不會把符合條件的
    欄位清單本身回傳給呼叫端,避免欄位數量過多時塞爆對話。

    參數:
        database_path: DuckDB 資料庫檔案的路徑。
        table_name: 要分析的資料表名稱。
        group_column: 分組欄位(類別型),ANOVA 用來分組比較的依據。
        pattern: 欄位名稱比對的字串。
        match_type: 比對規則,必須是以下三者之一:
            - "contains": 欄位名稱包含 pattern。
            - "startswith": 欄位名稱開頭是 pattern。
            - "endswith": 欄位名稱結尾是 pattern。

    回傳一個 dict,包含:
        - stats_name: 完整統計結果(所有成功計算的欄位,未截斷)所在的表名。
          若使用者想要 results 以外的排序方式或篩選條件(例如改用 f_stat 排序、
          只看某個 p_value 範圍),可以直接對這張表下 SQL 查詢,不需要重新
          呼叫這個工具。若沒有任何欄位成功算出結果,則為 None。
        - total_tested: 符合命名規則、實際被嘗試分析的欄位總數。
        - valid_count: 成功算出 ANOVA 結果的欄位數。
        - skipped_count: 因為非數值或分組數不足而被跳過的欄位數。
        - results: 依 p_value 由小到大排序的結果清單(每筆含 column、f_stat、p_value),最多 20 筆。
        - skipped: 被跳過欄位的清單(每筆含 column、error 原因),最多 20 筆。
        - truncated: bool,True 代表 results 只是部分結果(valid_count > 20)。
    """
    if match_type not in MATCH_TYPES:
        raise Exception(f"MCP Tool anova_by_pattern 錯誤: match_type 必須是 {MATCH_TYPES} 之一")

    try:
        value_columns = _find_cols_with_pattern(database_path, table_name, pattern, match_type)
        results = _run_anova(database_path, table_name, group_column, value_columns)
        stats_name = _save_results(database_path, results)
    except Exception as e:
        raise Exception(f"MCP Tool anova_by_pattern 執行錯誤: {e}")

    summary = _summarize(results)
    summary["stats_name"] = stats_name
    return summary


def main() -> None:
    mcp.run(transport="streamable-http")
    return


if __name__ == "__main__":
    main()

# INFO:     Started server process [9744]
# INFO:     Waiting for application startup.
# StreamableHTTP session manager started
# INFO:     Application startup complete.
# INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
# Created new transport with session ID: e903f7b044f349169a01d6f2792ee7b3
# INFO:     127.0.0.1:63334 - "POST /mcp HTTP/1.1" 200 OK
# INFO:     127.0.0.1:63335 - "POST /mcp HTTP/1.1" 202 Accepted
# INFO:     127.0.0.1:63336 - "GET /mcp HTTP/1.1" 200 OK