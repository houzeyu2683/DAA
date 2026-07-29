"""
這是一個範例檔案，專門用來手動測試 tools/system.py 裡的工具。
可以試試看：

- preview_files(".")                                          # 看看目前資料夾的檔案
- search_files(".", "example_code.py")                        # 依檔名找這個檔案
- search_files_with_expression(".", r"example.*\\.py")        # 依正則找檔名
- read_file("example_code.py", 10, 20)                        # 分頁讀取內容
- search_code_in_file("example_code.py", "# TODO")             # 精確比對，會超過 12 筆，應該被截斷
- search_code_in_file("example_code.py", "class Cache:\\n    def __init__(self):")  # 跨行片段
- search_code_in_file_with_expression("example_code.py", r"def \\w+\\(")  # 正則抓所有函式定義
"""

import time


def add(a, b):
    # TODO: 補上型別檢查
    return a + b


def subtract(a, b):
    # TODO: 補上型別檢查
    return a - b


def multiply(a, b):
    # TODO: 補上型別檢查
    return a * b


def divide(a, b):
    # TODO: 補上除以零的例外處理
    return a / b


def power(a, b):
    # TODO: 補上負指數的處理
    return a ** b


def modulo(a, b):
    # TODO: 補上除以零的例外處理
    return a % b


def floor_divide(a, b):
    # TODO: 補上除以零的例外處理
    return a // b


class Cache:
    def __init__(self):
        self._store = {}

    def get(self, key):
        # TODO: 加上 miss 的 log
        return self._store.get(key)

    def set(self, key, value):
        # TODO: 加上容量上限
        self._store[key] = value


class Cache2:
    def __init__(self):
        self._store = {}

    def get(self, key):
        # TODO: 加上 miss 的 log
        return self._store.get(key)


class Cache3:
    def __init__(self):
        self._store = {}

    def get(self, key):
        # TODO: 加上 miss 的 log
        return self._store.get(key)


def slow_task():
    # TODO: 改成非同步版本
    time.sleep(1)
    return "done"


def fast_task():
    return "done"


def main():
    print(add(1, 2))
    print(subtract(5, 3))
    print(multiply(2, 3))
    print(divide(6, 2))
    print(power(2, 10))
    print(modulo(7, 2))
    print(floor_divide(7, 2))

    cache = Cache()
    cache.set("x", 1)
    print(cache.get("x"))


if __name__ == "__main__":
    main()
