import sys
import time

import duckdb

database_path = sys.argv[1]
worker_id = sys.argv[2]

try:
    connection = duckdb.connect(database=database_path)
    connection.execute("INSERT INTO counter VALUES (?)", [worker_id])
    time.sleep(1.0)
    connection.close()
    print(f"worker {worker_id}: 成功")
except Exception as error:
    print(f"worker {worker_id}: 失敗 -> {type(error).__name__}: {error}")
