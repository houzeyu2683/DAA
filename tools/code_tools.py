import io
import types
import contextlib
from langchain.tools import tool

_python_variables = {}


def _summarize(value) -> str:
    if hasattr(value, "shape"):
        return f"{type(value).__name__}(shape={value.shape})"
    if hasattr(value, "__len__") and not isinstance(value, str):
        return f"{type(value).__name__}(len={len(value)})"

    try:
        text = repr(value)
    except Exception:
        return f"{type(value).__name__}(repr failed)"

    text = text.replace("\n", "\\n")
    return text if len(text) <= 50 else text[:25] + "<...>" + text[-25:]


@tool
def preview_python_variables() -> dict:
    """預覽目前 Python 執行環境中的變數，只回傳精簡摘要，不含完整內容。
    最多顯示 12 個變數，total 會標示實際總數，超過 12 個時可以搭配
    find_python_variable 依名稱縮小範圍查詢。
    """
    candidates = {
        name: value
        for name, value in _python_variables.items()
        if not name.startswith("__") and not isinstance(value, types.ModuleType)
    }

    preview_items = list(candidates.items())[:12]
    return {
        "variables": {name: _summarize(value) for name, value in preview_items},
        "total": len(candidates),
    }


@tool
def run_python_code(code: str) -> str:
    """執行一段 Python 程式碼，並回傳標準輸出內容。
    程式碼在同一個 session 共用同一份變數空間，之前建立的變數/import 可以繼續沿用。
    """
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        exec(code, _python_variables)
    return output.getvalue()