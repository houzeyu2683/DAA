import os
import re
import platform
import subprocess
from collections import Counter
from pathlib import Path
import duckdb
import pandas as pd
from langchain.tools import tool


# def _resolve_within_workspace(workspace: str, relative_path: str) -> Path:
#     """把 relative_path 解析成絕對路徑，並確保結果沒有跳脫 workspace 範圍。"""
#     base = Path(workspace).resolve()
#     target = (base / relative_path).resolve()
#     if not target.is_relative_to(base):
#         raise ValueError(f"路徑 {relative_path} 超出 workspace 範圍，不允許存取。")
#     return target


@tool
def open_image(image_path: str) -> str:
    """
    打開一張圖片，會用作業系統預設的看圖軟體跳出視窗顯示。
    """
    # target = _resolve_within_workspace(workspace, image_path)
    
    if not os.path.isfile(image_path):
        return f"找不到圖片檔案：{image_path}"

    system = platform.system()
    if system == "Windows":
        os.startfile(image_path)
    # elif system == "Darwin":
    #     subprocess.run(["open", str(target)], check=True)
    # else:
    #     subprocess.run(["xdg-open", str(target)], check=True)

    return f"已開啟圖片：{image_path}"


# def preview_files(folder_path: str) -> str:
#     """瀏覽有哪些檔案"""
#     return True


# def find_files(folder_path: str, files_pattern: dict) -> str:
#     """尋找某個資料夾底下的檔案"""
#     return True
