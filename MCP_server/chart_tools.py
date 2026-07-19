import matplotlib


matplotlib.use("Agg")
import matplotlib.pyplot as plt
from fastmcp import FastMCP
import duckdb
from pathlib import Path
import dotenv
import os


dotenv.load_dotenv()
SERVER_NAME = os.getenv("MCP_CHART_SERVER_NAME")
SERVER_URL = os.getenv("MCP_CHART_SERVER_URL")
SERVER_PORT = os.getenv("MCP_CHART_SERVER_PORT")


mcp = FastMCP(SERVER_NAME)


@mcp.tool()
def read_statistic_table(database_path: str, statistic_table_name: str, top_number: int = 20) -> dict:
    """查看統計結果表中差異最顯著的前 N 筆資料(所有統計工具都會依 p_value 
    由小到大排序後保存到資料庫中(p_value 越小代表差異越顯著)。

    參數:
        database_path: DuckDB 資料庫檔案的路徑。
        statistic_table_name: 統計結果表名稱(例如 anova_with_cats_and_nums 產生的表)。
        top_number: 要取出的筆數，預設從差異最大開始取前 20 筆
    """

    print('start "read_statistic_table"')

    con = duckdb.connect(database_path, read_only=True)
    try:
        df = con.execute(
            f"SELECT * FROM {statistic_table_name}"
        ).df()
    finally:
        con.close()

    if df.empty:
        return f"表 {statistic_table_name} 沒有資料。"

    df = df.head(top_number) if top_number >= 0 else df.tail(-top_number)

    return {"overview": df.to_string()}


@mcp.tool()
def plot_box_chart(
    database_path: str, 
    table_name: str, 
    category_name: str, 
    numeric_name: str, 
    image_path: str
) -> str:
    """對指定表裡的類別欄位(category_name)與數值欄位(numeric_name)畫箱型圖(box chart)，
    圖片存成 PNG 檔案，回傳檔案路徑與簡短說明文字。

    參數:
        database_path: DuckDB 資料庫檔案的路徑。
        table_name: 資料表名稱(需為含有逐筆資料的原始表，不能是統計結果表)。
        category_name: 類別欄位名稱(分組依據，畫在 x 軸)。
        numeric_name: 數值欄位名稱(要畫分布的對象，畫在 y 軸)。
        image_path: 圖檔輸出路徑(建議放在 workspace 底下)。
    """

    print('start "plot_box_chart"')
    con = duckdb.connect(database_path, read_only=True)
    try:
        all_cols = [row[0] for row in con.execute(f"DESCRIBE {table_name}").fetchall()]
        if category_name not in all_cols or numeric_name not in all_cols:
            return f"欄位 {category_name} 或 {numeric_name} 不存在於表 {table_name} 中，未畫圖。"

        df = con.execute(f"SELECT {category_name}, {numeric_name} FROM {table_name}").df()
    finally:
        con.close()

    groups = {name: g[numeric_name].dropna() for name, g in df.groupby(category_name) if len(g) > 0}
    if len(groups) < 2:
        return f"欄位 {category_name} 的分組數量不足，未畫圖。"

    try:
        fig, ax = plt.subplots()
        ax.boxplot(groups.values(), tick_labels=list(groups.keys()))
        ax.set_xlabel(category_name)
        ax.set_ylabel(numeric_name)
        ax.set_title(f"{numeric_name} by {category_name}")
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
        fig.tight_layout()

        save_path = os.path.abspath(image_path)
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path)
        plt.close(fig)

    except Exception as e:
        print(e)

    return f"已將 {category_name} x {numeric_name} 的箱型圖存成圖檔，路徑：{save_path}"


if __name__ == "__main__":
    
    port = int(SERVER_PORT)
    mcp.run(transport="streamable-http", host=SERVER_URL, port=port)