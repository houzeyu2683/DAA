"""Shared DuckDB connection used only inside the MCP server process.

DuckDB only allows a single read-write connection to a database file at a
time, so every DuckDB access in this project (ingest + analysis) must happen
inside one process. That process is the MCP server; nothing else should
import this module.
"""

from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "warehouse.duckdb"

_connection: duckdb.DuckDBPyConnection | None = None


def get_connection() -> duckdb.DuckDBPyConnection:
    global _connection
    if _connection is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _connection = duckdb.connect(str(DB_PATH))
    return _connection


def resolve_path(path: str) -> Path:
    """Resolve a user-supplied path against the project root."""
    p = Path(path)
    return p if p.is_absolute() else (PROJECT_ROOT / p)
