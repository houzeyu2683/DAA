# DAA — 資料分析助手

這個專案的目標是打造一個資料分析助手（Agent）。

## 技術棧

目前預計使用的技術包含 LangGraph、LangChain、FastMCP、DuckDB、Pandas、Seaborn、Matplotlib、NumPy。

## 設計原則

在開始分析之前，我們需要為 Agent 準備好一系列基礎工具。

原則上，我們不會直接修改使用者的原始資料。

因此在分析使用者指定的資料之前，必須先將資料備份到資料庫。這個資料庫是整個分析流程的核心：分析過程中產生的所有中間表格都會存放在這裡，同時也要支援使用者隨時將表格匯出成方便編輯的 CSV 檔案，讓使用者可以把特徵工程或統計分析的結果帶走。

## 基礎工具

`is_file_exist(file_path: str) -> bool`
檢查檔案是否存在。

`create_database(database_path: str) -> bool`
新增一個資料庫。

`create_table(database_path: str, table_name: str, table_path: str)`
新增一張資料表。

`is_columns_exist(database_path: str, table_name: str, column_names: list) -> dict`
檢查欄位是否存在於資料表中。
範例：`{'user_id': True, 'user_name': False}`

`search_types_distribution_with_pattern(database_path: str, table_name: str, column_patterns: dict) -> dict`
依照欄位名稱的比對模式，回傳符合欄位的資料型別分佈。
`column_patterns` 格式為 `{'欄位名稱': '比對模式'}`，比對模式可以是：

- `equals`：完全相符，例如 `{'user_id': 'equals'}`
- `contains`：包含子字串，例如 `{'user_id': 'contains'}`
- `starts`：開頭符合，例如 `{'user_id': 'starts'}`
- `ends`：結尾符合，例如 `{'user_id': 'ends'}`

也可以一次指定多個欄位規則，例如 `{'user_id': 'ends', 'user_na': 'contains'}`。

`select_columns(database_path: str, table_name: str, column_names: list, checkpoint_name: str) -> dict`
查詢指定欄位，並將查詢結果另存為一個檢查點（checkpoint）表格。

`preview_table(database_path: str, table_name: str) -> dict`
預覽資料表內容。

`export_table(database_path: str, table_name: str, table_path: str)`
將資料表從資料庫匯出成檔案。
