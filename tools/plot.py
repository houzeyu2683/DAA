import os
import pandas as pd
import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot(database: str, view_name: str, code: str, save_path: str) -> dict:
    try:
        con = duckdb.connect(database)
        df = con.execute(f"SELECT * FROM {view_name}").fetchdf()
        con.close()

        size_mb = df.memory_usage(deep=True).sum() / 1024 / 1024
        if size_mb > 200:
            return {"error": f"view 太大 ({size_mb:.1f}MB)，請先用 SQL 縮小範圍"}

        save_path = os.path.expanduser(save_path)
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)

        plt.close("all")
        local_vars = {"df": df, "plt": plt, "pd": pd}
        exec(code, local_vars)
        plt.savefig(save_path, bbox_inches="tight", dpi=150)
        plt.close("all")

        return {"status": "完成", "filepath": save_path}
    except Exception as e:
        plt.close("all")
        return {"error": str(e)}
