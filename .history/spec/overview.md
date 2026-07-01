# DAA — Data Analysis Agent 規格書

## 目標

讓用戶透過自然語言對話，對自己上傳的資料做非線性的探索式分析：
- 用 SQL 撈資料
- 用 pandas 處理資料
- 用 matplotlib 視覺化資料

非線性意指：用戶可以隨時切換表、回到之前的 view、把多個結果合併再分析。

---

## 現有基礎

| 檔案 | 狀態 | 說明 |
|------|------|------|
| `sql_agent.py` | 已完成 | SQL 工具 + agent 主迴圈 |
| `session_demo.py` | 已完成（demo） | DuckDB view 作為 session 狀態的模式 |
| `.data/workspace.db` | 已存在 | 測試用 DuckDB 檔 |

---

## 前提假設

- `.duckdb` 檔案已存在（CSV 上傳與轉換為獨立流程，不在此 agent 範圍內）
- 用戶資料表可能 5-6GB 以上，禁止整表載入記憶體
- 測試方式：`python service.py`（之後再接前端）

---

## 專案結構

```
project/
├── service.py              # 入口：REPL 對話循環（之後可換成 FastAPI）
├── agent/
│   ├── agent.py            # LLM 對話循環 + tool dispatch
│   └── session.py          # Session 狀態管理
├── tools/
│   ├── sql.py              # SQL 工具
│   ├── pandas_tool.py      # pandas 工具
│   └── plot.py             # 畫圖工具
├── db/
│   └── connection.py       # DuckDB 連線管理
└── spec/
    └── overview.md         # 本文件
```

---

## Session 狀態設計

用 **DuckDB view** 作為狀態載體（參考 `session_demo.py`）：

```python
class Session:
    con: duckdb.Connection        # 指向該用戶的 .duckdb 檔
    views: dict[str, str]         # { "view_name": "描述" }
    messages: list                # 對話 history
```

- 每次 `run_sql` 可選擇 `save_as` 把結果存成 DuckDB view
- LLM 每輪對話前收到 `build_context()` 注入當前有哪些 view 可用
- View 存在 DuckDB 裡，不佔 Python 記憶體

---

## Tools 規格

### SQL 工具（`tools/sql.py`）

| Tool | 說明 |
|------|------|
| `list_tables()` | 列出所有原始表 |
| `describe_table(name)` | 回傳 schema（欄位名、型別） |
| `run_sql(query, save_as?)` | 執行查詢，可存成 view |
| `merge_views(view1, view2, on, save_as)` | JOIN 兩個 view |
| `export_file(query, filename)` | 匯出 CSV，不佔記憶體 |

**大小守衛**（`run_sql` 內）：
```python
size_mb = df.memory_usage(deep=True).sum() / 1024 / 1024
if size_mb > 50:
    return {"error": f"結果太大 ({size_mb:.1f}MB)", "hint": "..."}
```
- 同時擋掉行數過多和欄位過多兩種情況

### pandas 工具（`tools/pandas_tool.py`）

| Tool | 說明 |
|------|------|
| `pandas_run(code, view_name)` | 對指定 view 執行 pandas 程式碼，回傳摘要 |

- 從 DuckDB view 取資料，執行用戶/LLM 提供的 pandas 程式碼
- 只回傳摘要（shape、統計、前幾行），不把完整 DataFrame 放進 context

### 畫圖工具（`tools/plot.py`）

| Tool | 說明 |
|------|------|
| `plot(code, view_name, save_path)` | 對指定 view 畫圖，存到用戶指定路徑 |

- 用戶自己決定存哪裡（`save_path`）
- 回傳 `{"status": "完成", "filepath": save_path}`

---

## Context 管理策略

- **Observation Masking**：舊的 tool 輸出（大量資料預覽）不保留在 messages 裡，只保留摘要
- **`build_context()`**：每輪對話前注入當前 session 狀態，LLM 不需要翻歷史
- **目標**：即使對話很長，context 裡的資料量維持固定大小

---

## 使用者流程範例

```
用戶：我想看 tableA
  → list_tables() + describe_table("tableA")

用戶：挑 Equipment、CB_22、cp_eq1
  → run_sql("SELECT Equipment, CB_22, cp_eq1 FROM tableA", save_as="view_A1")

用戶：分析這幾欄的分布
  → pandas_run(code, "view_A1")

用戶：再看一下 tableB 的 CB_22 跟 wat_eq*
  → run_sql("SELECT Equipment, CB_22, wat_eq1, wat_eq2 FROM tableB", save_as="view_B1")

用戶：把 view_A1 跟 view_B1 合併
  → merge_views("view_A1", "view_B1", on="Equipment", save_as="view_merged")

用戶：畫圖存到 ~/Desktop/result.png
  → plot(code, "view_merged", "~/Desktop/result.png")
```

---

## 開發順序

1. `db/connection.py` — DuckDB 連線（假設 .db 已存在）
2. `tools/sql.py` — 整合現有 `sql_agent.py` 的 tools
3. `agent/session.py` — 整合 `session_demo.py` 的 session 模式
4. `agent/agent.py` — LLM 對話循環
5. `service.py` — REPL 入口，驗證完整流程
6. `tools/pandas_tool.py` — pandas 工具
7. `tools/plot.py` — 畫圖工具

---

## 暫不處理

- CSV 上傳與轉換流程
- 前端接入
- 跨 session 的長期記憶
- 用戶權限管理
