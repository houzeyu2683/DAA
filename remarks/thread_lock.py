"""
教學示範:threading.Lock 到底在防什麼、什麼時候有用、什麼時候沒用。

執行方式: python remarks/thread_lock.py

分成三組情境:

1. 經典 race condition(不涉及 DuckDB):多個執行緒同時對同一個共用變數做「讀取 -> 修改 -> 寫回」
   - 沒有鎖:最終結果常常「少算」,因為多個執行緒同時讀到舊值,後面的寫入把前面的覆蓋掉
   - 有鎖(用法跟 analysis.py 打算加的 _get_lock 完全一樣):結果一定正確,
     因為同一時間只有一個執行緒能完整做完「讀取 -> 修改 -> 寫回」

2. 同一個 process 內,多個執行緒同時寫入同一個 DuckDB 檔案
   -> 實測(DuckDB 1.5.4)不需要鎖也不會衝突,DuckDB 自己協調好了

3. 兩個「獨立 process」同時寫入同一個 DuckDB 檔案
   -> 會真的衝突,而且 threading.Lock 完全防不住(鎖只存在單一 process 記憶體內,
      跨 process 的兩份程式各自有各自的 _locks 字典,互相看不到對方)
"""

import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import duckdb


# ---- 跟 analysis.py 打算加的寫法完全一樣:每個 resource key 各自一把鎖 ----
_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _get_lock(key: str) -> threading.Lock:
    with _locks_guard:
        if key not in _locks:
            _locks[key] = threading.Lock()
        return _locks[key]


def increment_without_lock(counter: dict) -> None:
    current = counter["value"]
    time.sleep(0.0001)  # 刻意製造「讀到舊值」的空檔,放大 race condition
    counter["value"] = current + 1


def increment_with_lock(counter: dict) -> None:
    with _get_lock("demo-counter"):
        current = counter["value"]
        time.sleep(0.0001)
        counter["value"] = current + 1


def demo_counter_race() -> None:
    print("\n=== 情境 1: 經典 race condition,5 個執行緒各自把共用計數器 +1 做 20 次 ===")
    worker_count, times_each = 5, 20
    expected = worker_count * times_each

    counter = {"value": 0}
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        for _ in range(worker_count):
            executor.submit(lambda: [increment_without_lock(counter) for _ in range(times_each)])
    ok = "正確" if counter["value"] == expected else "錯誤,有更新被覆蓋掉了"
    print(f"  沒有鎖: 預期 {expected},實際 {counter['value']} ({ok})")

    counter = {"value": 0}
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        for _ in range(worker_count):
            executor.submit(lambda: [increment_with_lock(counter) for _ in range(times_each)])
    ok = "正確" if counter["value"] == expected else "錯誤"
    print(f"  有鎖:   預期 {expected},實際 {counter['value']} ({ok})")


def write_same_process_no_lock(database_path: str, worker_id: int) -> None:
    connection = duckdb.connect(database=database_path)
    connection.execute("INSERT INTO counter VALUES (?)", [str(worker_id)])
    time.sleep(0.2)
    connection.close()


def setup_db(database_path: str) -> None:
    connection = duckdb.connect(database=database_path)
    connection.execute("CREATE TABLE counter (worker_id VARCHAR)")
    connection.close()


def demo_same_process_duckdb() -> None:
    print("\n=== 情境 2: 同一個 process,5 個執行緒同時寫入同一個 DuckDB 檔案(沒加鎖) ===")

    with tempfile.TemporaryDirectory() as tmp_dir:
        database_path = f"{tmp_dir}/demo.db"
        setup_db(database_path)

        success, failed = 0, 0
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(write_same_process_no_lock, database_path, i) for i in range(5)]
            for future in futures:
                try:
                    future.result()
                    success += 1
                except Exception as error:
                    failed += 1
                    print(f"  失敗 -> {type(error).__name__}: {error}")

        print(f"  結果: 成功 {success} / 失敗 {failed}")
        print("  => 同一個 process 內,DuckDB 自己就處理好併發了,這個情境不需要額外加鎖。")


def demo_cross_process_duckdb() -> None:
    print("\n=== 情境 3: 兩個「獨立 process」同時寫入同一個 DuckDB 檔案 ===")

    with tempfile.TemporaryDirectory() as tmp_dir:
        database_path = f"{tmp_dir}/demo.db"
        setup_db(database_path)

        worker_script = __file__.replace("thread_lock.py", "_cross_process_worker.py")

        process_a = subprocess.Popen(
            [sys.executable, worker_script, database_path, "A"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
        )
        time.sleep(0.2)  # 確保 A 已經先搶到連線
        process_b = subprocess.Popen(
            [sys.executable, worker_script, database_path, "B"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
        )

        output_a, _ = process_a.communicate()
        output_b, _ = process_b.communicate()
        print(f"  process A: {output_a.strip()}")
        print(f"  process B: {output_b.strip()}")
        print("  => 跨 process 才是 DuckDB 真正的單一寫入者限制發生的地方,")
        print("     而 threading.Lock 只存在單一 process 記憶體內,救不了這個情境。")


if __name__ == "__main__":
    demo_counter_race()
    demo_same_process_duckdb()
    demo_cross_process_duckdb()
