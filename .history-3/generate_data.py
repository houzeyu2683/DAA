import os
import string
import numpy as np
import pandas as pd


def generate_data(nrow: int, device_ncol: int, device_group: list, out_csv: str) -> pd.DataFrame:
    """
    生成假資料並存成 CSV。

    Parameters
    ----------
    nrow : int
        資料筆數。
    device_ncol : int
        類別欄位（device）的數量。
    device_group : list
        長度需等於 device_ncol，對應每個欄位的類別數量。
    out_csv : str
        CSV 輸出路徑，例如 "./data.csv"

    Returns
    -------
    pandas.DataFrame
        生成的 DataFrame。
    """

    if len(device_group) != device_ncol:
        raise ValueError("device_group 的長度必須等於 device_ncol")

    # 數值欄位 sensor_avg
    data = {
        "sensor_avg": np.random.rand(nrow).astype(np.float32)
    }

    # 類別欄位 device_1 ~ device_{device_ncol}
    for i, ncategory in enumerate(device_group, start=1):
        categories = [f"cat_{string.ascii_uppercase[j % 26]}{j // 26}" for j in range(ncategory)]
        data[f"device_{i}"] = np.random.choice(categories, size=nrow)

    df = pd.DataFrame(data)

    # 建立資料夾(如果不存在)
    os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)

    df.to_csv(out_csv, index=False)

    return df


def generate_device_column(nrow: int, device_index: int, outpath: str) -> pd.DataFrame:
    """
    生成單一類別欄位並存成 CSV。

    Parameters
    ----------
    nrow : int
        資料筆數。
    device_index : int
        欄位編號，欄位名稱為 device_{device_index}。
    outpath : str
        CSV 輸出路徑，例如 "./data.csv"

    Returns
    -------
    pandas.DataFrame
        生成的 DataFrame。
    """

    # 類別數量從 15~50 隨機挑一個
    K = np.random.randint(15, 51)

    # 類別名稱 gcat_{device_index}_{1} ~ gcat_{device_index}_{K}
    categories = [f"gcat_{device_index}_{k}" for k in range(1, K + 1)]

    data = {
        f"device_{device_index}": np.random.choice(categories, size=nrow)
    }

    df = pd.DataFrame(data)

    os.makedirs(os.path.dirname(outpath) or ".", exist_ok=True)

    df.to_csv(outpath, index=False)

    return df


def generate_device_table(nrow: int, device_ncol: int, outpath: str) -> pd.DataFrame:
    """
    迴圈生成 device_1 ~ device_{device_ncol} 欄位並合併存成 CSV。

    Parameters
    ----------
    nrow : int
        資料筆數。
    device_ncol : int
        欄位數量。
    outpath : str
        CSV 輸出路徑，例如 "./data.csv"

    Returns
    -------
    pandas.DataFrame
        生成的 DataFrame。
    """

    data = {}
    for device_index in range(1, device_ncol + 1):
        K = np.random.randint(15, 51)
        categories = [f"gcat_{device_index}_{k}" for k in range(1, K + 1)]
        data[f"device_{device_index}"] = np.random.choice(categories, size=nrow)

    df = pd.DataFrame(data)

    os.makedirs(os.path.dirname(outpath) or ".", exist_ok=True)

    df.to_csv(outpath, index=False)

    return df


if __name__ == '__main__':
    nrow = 1000
    device_ncol = 3
    device_group = [2, 3, 5]
    out_csv = './.data/generated_frame.csv'

    generate_data(nrow, device_ncol, device_group, out_csv)
