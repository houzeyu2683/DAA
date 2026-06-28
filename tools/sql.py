import json
import os

_FORBIDDEN = {"drop", "delete", "update", "insert", "alter", "create", "truncate"}


def _is_select_only(query: str) -> bool:
    lowered = query.lower()
    return not any(word in lowered for word in _FORBIDDEN)


def list_tables(session) -> str:
    result = session.con.execute("SHOW TABLES").fetchall()
    tables = [row[0] for row in result]
    return json.dumps({"tables": tables}, ensure_ascii=False)


def describe_table(session, table_name: str) -> str:
    try:
        result = session.con.execute(f"DESCRIBE {table_name}").fetchall()
        columns = [{"name": row[0], "type": row[1]} for row in result]
        return json.dumps({"table": table_name, "columns": columns}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


def run_sql(session, query: str, save_as: str = None) -> str:
    if not _is_select_only(query):
        return json.dumps({"error": "只允許 SELECT 查詢"})
    try:
        df = session.con.execute(query).fetchdf()

        size_mb = df.memory_usage(deep=True).sum() / 1024 / 1024
        if size_mb > 50:
            return json.dumps({
                "error": f"結果太大 ({size_mb:.1f}MB)",
                "hint": f"{len(df)} 行 × {len(df.columns)} 欄，請加 WHERE/GROUP BY 或減少欄位"
            })

        if save_as:
            session.con.execute(f"CREATE OR REPLACE VIEW {save_as} AS {query}")
            session.views[save_as] = f"來自查詢: {query[:80]}"

        preview = df.head(5)
        return json.dumps({
            "shape": list(df.shape),
            "columns": list(df.columns),
            "preview": preview.to_dict(orient="records"),
            "saved_as": save_as
        }, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def merge_views(session, view1: str, view2: str, on: str, save_as: str) -> str:
    query = f"SELECT * FROM {view1} JOIN {view2} USING ({on})"
    try:
        session.con.execute(f"CREATE OR REPLACE VIEW {save_as} AS {query}")
        session.views[save_as] = f"{view1} JOIN {view2} ON {on}"
        preview = session.con.execute(f"SELECT * FROM {save_as} LIMIT 5").fetchdf()
        return json.dumps({
            "shape": list(preview.shape),
            "columns": list(preview.columns),
            "preview": preview.to_dict(orient="records"),
            "saved_as": save_as
        }, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def export_file(session, query: str, filename: str) -> str:
    if not _is_select_only(query):
        return json.dumps({"error": "只允許 SELECT 查詢"})
    try:
        os.makedirs("./exports", exist_ok=True)
        filepath = f"./exports/{filename}.csv"
        session.con.execute(f"COPY ({query}) TO '{filepath}' (HEADER, DELIMITER ',')")
        size_mb = round(os.path.getsize(filepath) / (1024 * 1024), 2)
        return json.dumps({"status": "完成", "filepath": filepath, "size_mb": size_mb}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})
