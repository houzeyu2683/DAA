"""MCP server exposing DuckDB-backed tools to the agent.

This process owns the only read-write connection to data/warehouse.duckdb.
Both the agent's tool calls and the middleware's deterministic CSV ingestion
talk to this single process over HTTP, so there is never more than one
DuckDB writer.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from fastmcp import FastMCP

from duckdb_lib.connection import PROJECT_ROOT, get_connection
from duckdb_lib.ingest import ingest_csv as _ingest_csv

load_dotenv()

OUTPUT_DIR = PROJECT_ROOT / "data" / "outputs"

mcp = FastMCP("reDAA-duckdb")


@mcp.tool
def ingest_csv(path: str) -> dict:
    """Load a CSV file into DuckDB as a table (create-or-replace).

    Not meant to be called by the agent directly: the CsvIngestMiddleware
    calls this deterministically whenever a user message mentions a CSV
    path. Exposed as a tool so ingestion happens through the same DuckDB
    connection as every other tool in this server.
    """
    return _ingest_csv(path)


@mcp.tool
def list_tables() -> list[str]:
    """List every table currently available in DuckDB."""
    con = get_connection()
    return [row[0] for row in con.execute("SHOW TABLES").fetchall()]


@mcp.tool
def get_schema(table: str) -> list[dict]:
    """Get column names and types for a DuckDB table."""
    con = get_connection()
    return [
        {"name": row[0], "type": row[1]}
        for row in con.execute(f'DESCRIBE "{table}"').fetchall()
    ]


@mcp.tool
def compute_group_difference(
    table: str,
    value_column: str,
    column_filter: str = "",
    top_k: int = 5,
) -> list[dict]:
    """Rank categorical columns by how much they split `value_column` apart.

    For each candidate categorical column, groups rows by that column's
    values, computes the mean of `value_column` per group, and scores the
    column as (max group mean - min group mean) using only groups with at
    least 2 rows. Returns the `top_k` columns with the largest score,
    descending.

    Args:
        table: DuckDB table name.
        value_column: Numeric column to analyze differences on.
        column_filter: Only consider columns whose name contains this
            substring (case-insensitive). Empty string means consider every
            other column.
        top_k: How many top columns to return.
    """
    con = get_connection()
    schema = con.execute(f'DESCRIBE "{table}"').fetchall()
    candidates = [
        row[0]
        for row in schema
        if row[0] != value_column
        and (column_filter.lower() in row[0].lower() if column_filter else True)
    ]

    results = []
    for col in candidates:
        rows = con.execute(
            f'SELECT "{col}" AS grp, AVG("{value_column}") AS mean_val, COUNT(*) AS n '
            f'FROM "{table}" WHERE "{col}" IS NOT NULL GROUP BY "{col}" HAVING COUNT(*) >= 2'
        ).fetchall()
        if len(rows) < 2:
            continue
        means = [r[1] for r in rows]
        results.append(
            {
                "column": col,
                "score": max(means) - min(means),
                "n_groups": len(rows),
            }
        )

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:top_k]


@mcp.tool
def plot_boxplot(table: str, value_column: str, group_column: str) -> dict:
    """Draw a box chart of `value_column` grouped by `group_column`.

    Saves a PNG under data/outputs/ and returns its path so the caller can
    tell the user where to find it.
    """
    con = get_connection()
    rows = con.execute(
        f'SELECT "{group_column}" AS grp, "{value_column}" AS val FROM "{table}" '
        f'WHERE "{group_column}" IS NOT NULL AND "{value_column}" IS NOT NULL'
    ).fetchall()

    groups: dict[str, list[float]] = {}
    for grp, val in rows:
        groups.setdefault(str(grp), []).append(val)

    ordered = sorted(groups.items(), key=lambda kv: sum(kv[1]) / len(kv[1]), reverse=True)
    labels = [k for k, _ in ordered]
    data = [v for _, v in ordered]

    fig, ax = plt.subplots(figsize=(max(6, len(labels) * 0.4), 5))
    ax.boxplot(data, tick_labels=labels)
    ax.set_xlabel(group_column)
    ax.set_ylabel(value_column)
    ax.set_title(f"{value_column} by {group_column}")
    plt.xticks(rotation=90)
    fig.tight_layout()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{table}__{group_column}__boxplot.png"
    fig.savefig(out_path)
    plt.close(fig)

    return {"path": str(out_path), "n_groups": len(labels)}


if __name__ == "__main__":
    url = os.environ.get("DATA_SERVER_URL", "http://localhost:8001")
    host = url.split("://")[-1].split(":")[0]
    port = int(url.rsplit(":", 1)[-1])
    mcp.run(transport="http", host=host, port=port)
