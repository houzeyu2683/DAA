import pandas as pd
import duckdb


def pandas_run(database: str, view_name: str, code: str) -> dict:
    try:
        con = duckdb.connect(database)
        df = con.execute(f"SELECT * FROM {view_name}").fetchdf()
        con.close()

        size_mb = df.memory_usage(deep=True).sum() / 1024 / 1024
        if size_mb > 200:
            return {"error": f"view 太大 ({size_mb:.1f}MB)，請先用 SQL 縮小範圍"}

        local_vars = {"df": df, "pd": pd}
        exec(code, local_vars)

        result = local_vars.get("result", None)
        if result is None:
            return {"error": "程式碼沒有設定 result 變數"}

        if isinstance(result, pd.DataFrame):
            return {
                "type": "dataframe",
                "shape": list(result.shape),
                "preview": result.head(10).to_dict(orient="records"),
            }
        else:
            return {"type": "value", "result": str(result)}
    except Exception as e:
        return {"error": str(e)}
