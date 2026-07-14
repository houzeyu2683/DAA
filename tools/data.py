import re
import uuid
import os
import duckdb
import numpy as np
import pandas as pd
from collections import Counter
from pathlib import Path
from langchain.tools import tool

def _get_schema(database_path: str, table_name: str) -> dict:

    con = duckdb.connect(database_path, read_only=True)
    try:
        description = con.execute(f"DESCRIBE {table_name}").fetchall()
        # [
        #  ('player_id', 'VARCHAR', 'YES', None, None, None), 
        #  ('player_name', 'VARCHAR', 'YES', None, None, None), 
        #  ('age', 'BIGINT', 'YES', None, None, None), 
        #  ...... 
        #  ('player_of_match_awards', 'BIGINT', 'YES', None, None, None), 
        #  ('tournament_rating', 'DOUBLE', 'YES', None, None, None)
        # ]
        con.close()
    except Exception as e:
        con.close()
        raise Exception(f"_get_schema 執行錯誤: {e}")
    
    cols = [{"name": col[0], "type": col[1]} for col in description]
    total = len(description)
    types = dict(Counter(col[1] for col in description))
    schema = {
        'cols': cols,
        'total': total,
        'types': types
    }
    return schema


@tool()
def get_schema(database_path: str, table_name: str) -> dict:
    """
    查詢指定資料表的 schema(欄位資訊)。

    參數:
        database_path: DuckDB 資料庫檔案的路徑。
        table_name: 要查詢的資料表名稱。

    回傳一個 dict,包含:
        - cols: 欄位清單(每個元素含 name、type),最多只回傳前 16 個欄位。
        - total: 該表實際的總欄位數。
        - types: 各型別出現的次數統計,例如 {"VARCHAR": 7, "BIGINT": 32}。
        - truncated: bool,
            - True 代表 cols 只是部分欄位的預覽(total > 16 時被截斷)
            - False 代表 cols 就是完整清單。

    注意:當 total > 16 時,cols 只是部分欄位的預覽,並非完整清單。
    """
    head = 16
    try:
        schema = _get_schema(database_path, table_name)
    except Exception as e:
        return {"error": f"get_schema 執行錯誤: {e}"}

    if schema['total'] > head:
        schema['cols'] = schema['cols'][:head]
        schema['truncated'] = True
    else:
        schema['truncated'] = False

    return schema


def _make_table_name(filename: str) -> str:
    name = filename.rsplit(".", 1)[0].lower()
    name = re.sub(r"[^a-z0-9_]", "_", name)
    name = name.strip("_") or "table"
    suffix = uuid.uuid4().hex[:6]
    return f"raw_{name}_{suffix}"


@tool()
def load_table(table_path: str, database_path: str) -> dict:
    """讀取一份 CSV 檔案,寫入指定的 DuckDB 資料庫,成為一張新的表。

    表名會根據原始檔名自動產生(轉小寫、非英數字元換成底線),
    並附加一段隨機碼避免重名衝突,例如 sales-2024.csv
    會建成類似 raw_sales_2024_a3f9c2 這樣的表名。

    參數:
        table_path: CSV 檔案的路徑。
        database_path: 要寫入的 DuckDB 資料庫檔案路徑。

    回傳一個 dict,包含:
        - table_name: 實際建立的表名。
        - csv_filename: 使用者原始的檔名,方便之後對照。
        - rows: 這張表寫入的資料筆數。
    """
    csv_filename = os.path.basename(table_path)
    table_name = _make_table_name(csv_filename)

    try:
        df = pd.read_csv(table_path)
    except Exception as e:
        return {"error": f"load_table 讀取 CSV 失敗: {e}"}

    Path(database_path).parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(database_path)
    try:
        con.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM df")
        con.close()
    except Exception as e:
        con.close()
        return {"error": f"load_table 寫入資料庫失敗: {e}"}

    nrow = len(df)
    return {
        "table_name": table_name,
        "csv_filename": csv_filename,
        "nrow": nrow,
    }
