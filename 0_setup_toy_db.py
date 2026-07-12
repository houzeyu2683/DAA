"""
建立這系列 notebook 共用的玩具 DuckDB 資料庫,只需要跑一次:
    conda run -n DAA python notebooks\0_setup_toy_db.py

表 sensor_readings 故意混了 device_ 開頭跟非 device_ 開頭的欄位,
用來練習「篩欄位名 + 算 correlation」這個情境,不需要事先窮舉這個組合
成一個固定工具。
"""

import duckdb
import numpy as np
import pandas as pd

DB_PATH = "notebooks/toy.db"


def main() -> None:
    rng = np.random.default_rng(42)
    n = 200

    device_a = rng.normal(0, 1, n)
    device_b = device_a * 0.8 + rng.normal(0, 0.5, n)  # 跟 device_a 有明顯相關
    device_c = rng.normal(5, 2, n)  # 跟前兩者無關
    location = rng.integers(1, 4, n)  # 非 device_ 欄位,用來確認篩選有正確排除它

    df = pd.DataFrame(
        {
            "id": range(1, n + 1),
            "device_a": device_a,
            "device_b": device_b,
            "device_c": device_c,
            "location": location,
        }
    )

    con = duckdb.connect(DB_PATH)
    con.execute("CREATE OR REPLACE TABLE sensor_readings AS SELECT * FROM df")
    con.close()
    print(f"建好 {DB_PATH},表 sensor_readings,共 {n} 筆,欄位: {list(df.columns)}")


if __name__ == "__main__":
    main()
