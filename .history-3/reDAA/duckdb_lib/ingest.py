"""Deterministic CSV -> DuckDB ingestion. No LLM judgment involved here."""

import re

from duckdb_lib.connection import get_connection, resolve_path


def _table_name_from_path(path: str) -> str:
    stem = path.rsplit("/", 1)[-1]
    stem = stem[: -len(".csv")] if stem.lower().endswith(".csv") else stem
    name = re.sub(r"[^0-9a-zA-Z_]", "_", stem)
    if not name or name[0].isdigit():
        name = f"t_{name}"
    return name.lower()


def ingest_csv(path: str) -> dict:
    """Load a CSV file into DuckDB as a table, creating/replacing it.

    Returns the table name, row count, and column schema so callers (the
    middleware, the agent) know what to query next.
    """
    resolved = resolve_path(path)
    if not resolved.exists():
        raise FileNotFoundError(f"CSV not found: {resolved}")

    table = _table_name_from_path(path)
    con = get_connection()
    con.execute(
        f'CREATE OR REPLACE TABLE "{table}" AS '
        f"SELECT * FROM read_csv_auto(?)",
        [str(resolved)],
    )
    row_count = con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
    columns = [
        {"name": row[0], "type": row[1]}
        for row in con.execute(f'DESCRIBE "{table}"').fetchall()
    ]
    return {"table": table, "source_path": str(resolved), "row_count": row_count, "columns": columns}
