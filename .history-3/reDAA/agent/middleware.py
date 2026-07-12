"""Deterministic pre-processing middleware for the ReAct agent."""

import re

from langchain.agents.middleware import AgentMiddleware, AgentState
from langchain_core.messages import SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.runtime import Runtime

CSV_PATH_RE = re.compile(r'[^\s"\']+\.csv')


class CsvIngestMiddleware(AgentMiddleware):
    """Loads any CSV path mentioned in the latest user message into DuckDB.

    This runs before every model call, independent of what the LLM decides.
    "Any CSV the user mentions goes into DuckDB" is a fixed rule with no
    ambiguity, so it does not belong in the system prompt or behind an
    agent-callable tool -- it belongs here, in code that always runs.
    """

    def __init__(self, mcp_client: MultiServerMCPClient, server_name: str = "duckdb"):
        self._client = mcp_client
        self._server_name = server_name
        self._ingested_paths: set[str] = set()

    async def abefore_model(self, state: AgentState, runtime: Runtime) -> dict | None:
        last_human = next(
            (m for m in reversed(state["messages"]) if m.type == "human"), None
        )
        if last_human is None or not isinstance(last_human.content, str):
            return None

        paths = [
            p for p in CSV_PATH_RE.findall(last_human.content)
            if p not in self._ingested_paths
        ]
        if not paths:
            return None

        notes = []
        async with self._client.session(self._server_name) as session:
            for path in paths:
                result = await session.call_tool("ingest_csv", {"path": path})
                if result.isError:
                    notes.append(f'- 載入 "{path}" 失敗: {result.content}')
                    continue
                data = result.structuredContent
                self._ingested_paths.add(path)
                col_names = [c["name"] for c in data["columns"]]
                notes.append(
                    f'- "{path}" 已載入 DuckDB table `{data["table"]}`'
                    f'({data["row_count"]} 列, {len(col_names)} 欄, '
                    f'欄位包含: {col_names[:8]}{"..." if len(col_names) > 8 else ""})'
                )

        return {
            "messages": [
                SystemMessage(
                    content=(
                        "[系統自動載入]\n"
                        + "\n".join(notes)
                        + "\n之後的分析請一律對上述 DuckDB table 查詢,"
                        "不要嘗試直接讀取 CSV 檔案內容。"
                    )
                )
            ]
        }
