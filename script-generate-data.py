import os
import numpy as np
import pandas as pd
import duckdb

def generate_virtual_table(nrows: int, outpath: str) -> bool:
    """
    生成虛擬資料並存成 CSV。

    Parameters
    ----------
    nrows : int
        要生成的資料筆數。
    outpath : str
        CSV 輸出路徑，例如 "./data.csv"

    Returns
    -------
    pandas.DataFrame
        生成的 DataFrame。
    """

    # 200 台 machine
    machines = [f"machine_{i}" for i in range(1, 21)]

    # Equipment 欄位
    data = {
        "Equipment": np.random.choice(machines, size=nrows)
    }

    # CP_1 ~ CP_1800
    for i in range(1, 1800+1):
        data[f"CP_{i}"] = np.random.rand(nrows).astype(np.float32)
    
    # TF_1 ~ TF_3800
    for i in range(1, 3800+1):
        data[f"TF_{i}"] = np.random.rand(nrows).astype(np.float32)

    # WAT_1 ~ WAT_2800
    for i in range(1, 2800+1):
        data[f"WAT_{i}"] = np.random.rand(nrows).astype(np.float32)

    # 建立 DataFrame
    df = pd.DataFrame(data)

    # 建立資料夾(如果不存在)
    os.makedirs(os.path.dirname(outpath) or ".", exist_ok=True)

    # 存成 CSV
    df.to_csv(outpath, index=False)

    # duckdb
    con = duckdb.connect('./.data/workspace.db')
    con.register("df", df)
    con.execute("CREATE TABLE my_table AS SELECT * FROM df")
    con.close()

    return True

if __name__ =='__main__':
    nrows = 5000
    outpath = './.data/frame.csv'
    
    generate_virtual_table(nrows, outpath)
