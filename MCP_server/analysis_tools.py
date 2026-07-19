from fastmcp import FastMCP
import duckdb
from pathlib import Path
import dotenv
import os
import pandas as pd
from collections import Counter
import uuid
from typing import Optional
from scipy import stats


STATS_METRICS = {
    "difference_analysis": "p_value"
}


dotenv.load_dotenv()
SERVER_NAME = os.getenv("MCP_ANALYSIS_SERVER_NAME")
SERVER_URL = os.getenv("MCP_ANALYSIS_SERVER_URL")
SERVER_PORT = os.getenv("MCP_ANALYSIS_SERVER_PORT")


mcp = FastMCP(SERVER_NAME)


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


def _create_table(
    database_path: str, table_name: str, table_content: pd.DataFrame
) -> bool:

    con = duckdb.connect(database_path)
    con.register("table_content", table_content)
    con.execute(
        f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM table_content"
    )
    con.close()
    return True


@mcp.tool()
def get_table_shape(database_path: str, table_name: str) -> list:
    """獲得資料表的資料數與欄位數，回傳 [row_count, col_count]。

    參數:
        database_path: DuckDB 資料庫檔案的路徑。
        table_name: 要查詢的資料表名稱。
    """

    print('start "get_table_shape"')
    con = duckdb.connect(database_path, read_only=True)
    try:
        row_count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        col_count = len(con.execute(f"DESCRIBE {table_name}").fetchall())
    finally:
        con.close()
    return [row_count, col_count]


@mcp.tool()
def get_columns_type(database_path: str, table_name: str, columns_name: list) -> dict:
    """查詢資料表中指定欄位的型別。

    輸出格式範例: {"col_1": "BIGINT", "col_2": "VARCHAR", ....}

    參數:
        database_path: DuckDB 資料庫檔案的路徑。
        table_name: 要查詢的資料表名稱。
        columns_name: 要查詢型別的欄位名稱清單。
    """

    print('start "get_columns_type_distribution"')
    con = duckdb.connect(database_path, read_only=True)
    try:
        schema = con.execute(f"DESCRIBE {table_name}").fetchall()
    finally:
        con.close()
    types_by_col = {row[0]: row[1] for row in schema}
    return {col: types_by_col[col] for col in columns_name if col in types_by_col}


@mcp.tool()
def get_columns_type_distribution(database_path: str, table_name: str, columns_pattern: dict) -> dict:
    """依欄位名稱比對規則，統計符合條件的欄位中各種型別各有幾個。

    columns_pattern 格式是 {pattern字串: 比對方式}，例如:
        - {"XXXX": "contains"}   欄位名稱包含 "XXXX"
        - {"XXXX": "startwith"}  欄位名稱開頭是 "XXXX"
        - {"XXXX": "endwith"}    欄位名稱結尾是 "XXXX"

    輸出格式範例: {"BIGINT": 22, "VARCHAR": 123, ....}

    參數:
        database_path: DuckDB 資料庫檔案的路徑。
        table_name: 要查詢的資料表名稱。
        columns_pattern: 欄位名稱的比對規則。
    """

    print('start "get_columns_type_distribution"')
    con = duckdb.connect(database_path, read_only=True)
    try:
        schema = con.execute(f"DESCRIBE {table_name}").fetchall()
    finally:
        con.close()

    matched_types = []
    for row in schema:
        col_name, col_type = row[0], row[1]
        for pattern, mode in columns_pattern.items():
            if mode == "contains" and pattern in col_name:
                matched_types.append(col_type)
                break
            if mode == "startwith" and col_name.startswith(pattern):
                matched_types.append(col_type)
                break
            if mode == "endwith" and col_name.endswith(pattern):
                matched_types.append(col_type)
                break

    return dict(Counter(matched_types))


@mcp.tool()
def preview_columns(database_path: str, table_name: str) -> str:
    """列出資料表的所有欄位名稱，串成一個字串。

    若欄位數量小於等於 12 個，直接用逗號串接全部欄位；
    若超過 12 個，只顯示前 3 個與後 3 個欄位名稱，中間用 '......' 省略。

    參數:
        database_path: DuckDB 資料庫檔案的路徑。
        table_name: 要查詢的資料表名稱。
    """

    print('start "preview_columns"')
    con = duckdb.connect(database_path, read_only=True)
    try:
        columns = [row[0] for row in con.execute(f"DESCRIBE {table_name}").fetchall()]
    finally:
        con.close()

    if len(columns) <= 12:
        return ','.join(columns)
    return ','.join(columns[:3]) + '......' + ','.join(columns[-3:])


@mcp.tool()
def difference_analysis(
    database_path: str,
    table_name: str,
    stats_table_name: str, 
    categories: Optional[list] = None,
    categories_pattern: Optional[dict] = None,
    numerics: Optional[list] = None,
    numerics_pattern: Optional[dict] = None,
    top_number: int = 20
) -> dict:
    """對類別欄位與數值欄位做單因子 ANOVA。
    categories/numerics 各自可以是一個或多個欄位，用 list 明確列出欄位名稱。

    在比對之前，你需要去檢查欄位的類型

    如果欄位數量很多、無法一一列舉(例如所有包含某個字串的欄位)，
    改用 categories_pattern/numerics_pattern 比對欄位名稱，格式是 {pattern字串: 比對方式}，
    比對方式可以是 "contains"(包含)、"startwith"(開頭是)、"endwith"(結尾是)。

    categories 與 categories_pattern 必須只能擇一輸入；
    numerics 與 numerics_pattern 必須只能擇一輸入。

    內部會對「類別欄位 x 數值欄位」的每一種組合各跑一次 ANOVA，
    完整結果存入資料庫的一張新表，回傳依 p_value 排序後的截斷預覽文字。

    參數:
        database_path: DuckDB 資料庫檔案的路徑。
        table_name: 要分析的資料表名稱。
        categories: 類別欄位名稱清單。
        categories_pattern: 類別欄位的比對規則。
        numerics: 數值欄位名稱清單。
        numerics_pattern: 數值欄位的比對規則。
        top_number: 如果有指定想要看前幾個結果，可以用這個設定，預設是前20個
    """
    print('start "difference_analysis"')
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
        # print(cat, num) 
        return "沒有找到符合條件的類別欄位與數值欄位組合，未執行任何 ANOVA。"

    stats_metric = STATS_METRICS.get("difference_analysis")
    results_df = pd.DataFrame(results).sort_values(stats_metric)
    # print(results_df)
    
    #stats_table_name = stats_table_name + '_' + uuid.uuid4().hex[:4]

    _create_table(database_path, stats_table_name, results_df)

    top_rows = results_df.head(top_number)
    top_summary = "\n".join(
        f"{i+1}. {row['cat']} x {row['num']}（{stats_metric}={row[stats_metric]:.4e}）"
        for i, row in enumerate(top_rows.to_dict("records"))
    )
    conclusion = f"依照 {stats_metric} 排序，差異最顯著的前 {top_number} 個組合：\n{top_summary}"
    # print(conclusion)

    preview = results_df.to_string(max_rows=20, show_dimensions=False)
    return {
        "stats_table_name": {
            stats_table_name: "統計結果存放在此。"
        },
        "stats_table_preview": preview, 
        "stats_metric": {
            stats_metric: "分析主要依據的指標。"
        },     # 明確標註判斷依據
        "conclusion": conclusion
    }


if __name__ == "__main__":
    
    port = int(SERVER_PORT)
    mcp.run(transport="streamable-http", host=SERVER_URL, port=port)