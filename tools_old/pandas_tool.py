import json
import pandas as pd


def pandas_run(session, view_name: str, code: str) -> str:
    try:
        df = session.con.execute(f"SELECT * FROM {view_name}").fetchdf()

        size_mb = df.memory_usage(deep=True).sum() / 1024 / 1024
        if size_mb > 200:
            return json.dumps({
                "error": f"view 太大 ({size_mb:.1f}MB)，請先用 SQL 縮小範圍"
            })

        local_vars = {"df": df, "pd": pd}
        exec(code, local_vars)
        result = local_vars.get("result", df)

        if isinstance(result, pd.DataFrame):
            return json.dumps({
                "shape": list(result.shape),
                "dtypes": result.dtypes.astype(str).to_dict(),
                "describe": result.describe(include="all").to_dict(),
                "preview": result.head(5).to_dict(orient="records")
            }, ensure_ascii=False, default=str)
        else:
            return json.dumps({"result": str(result)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})
