import duckdb

_FORBIDDEN = {"drop", "delete", "update", "insert", "alter", "create", "truncate"}


def _is_select_only(query: str) -> bool:
    return not any(w in query.lower() for w in _FORBIDDEN)


def get_schema(database: str) -> str:
    con = duckdb.connect(database)
    schema_lines = []

    tables = con.execute("SHOW TABLES").fetchdf()["name"].tolist()
    for t in tables:
        cols = con.execute(f"DESCRIBE {t}").fetchdf()["column_name"].tolist()
        if len(cols) <= 20:
            col_str = ", ".join(cols)
        else:
            col_str = f"{', '.join(cols[:5])}, ..., {', '.join(cols[-3:])} ({len(cols)} 欄)"
        schema_lines.append(f"TABLE {t}: {col_str}")

    try:
        views = con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_type = 'VIEW'"
        ).fetchdf()["table_name"].tolist()
        for v in views:
            cols = con.execute(f"DESCRIBE {v}").fetchdf()["column_name"].tolist()
            if len(cols) <= 20:
                col_str = ", ".join(cols)
            else:
                col_str = f"{', '.join(cols[:5])}, ..., {', '.join(cols[-3:])} ({len(cols)} 欄)"
            schema_lines.append(f"VIEW {v}: {col_str}")
    except Exception:
        pass

    con.close()
    return "\n".join(schema_lines)


def run_sql(database: str, query: str, save_as: str = None) -> dict:
    if not _is_select_only(query):
        return {"error": "只允許 SELECT 查詢"}
    try:
        con = duckdb.connect(database)
        df = con.execute(query).fetchdf()

        size_mb = df.memory_usage(deep=True).sum() / 1024 / 1024
        if size_mb > 50:
            con.close()
            return {"error": f"結果太大 ({size_mb:.1f}MB)，請加 WHERE/GROUP BY 或減少欄位"}

        if save_as:
            con.execute(f"CREATE OR REPLACE VIEW {save_as} AS {query}")

        preview = df.head(3).to_dict(orient="records")
        con.close()
        return {
            "shape": list(df.shape),
            "columns": list(df.columns),
            "preview": preview,
            "saved_as": save_as,
        }
    except Exception as e:
        return {"error": str(e)}
