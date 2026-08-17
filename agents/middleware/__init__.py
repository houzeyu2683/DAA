from importlib.metadata import version

from packaging.version import Version

# ToolErrorMiddleware 是 langchain 1.3.14 才新增的。版本夠新就用官方版本，
# 版本太低（例如目前環境的 1.3.11）就退回用 agents/middleware/tool_error.py 這份複製版。
if Version(version("langchain")) >= Version("1.3.14"):
    from langchain.agents.middleware import ToolErrorMiddleware
else:
    from agents.middleware.tool_error import ToolErrorMiddleware

__all__ = ["ToolErrorMiddleware"]
