# Test Cases

## 工具層測試（tools_test.py 直接跑）

不透過 LLM，直接呼叫 tool function，驗證每個工具的行為。

### TC-01 list_tables — 基本查詢
```
預期：回傳 {"tables": ["my_table"]}
```

### TC-02 describe_table — 欄位結構
```
輸入：table_name="my_table"
預期：回傳 301 個欄位（Equipment + CP_1~CP_300），型別正確
```

### TC-03 run_sql — 正常查詢並存 view
```
輸入：
  query = "SELECT Equipment, CP_1, CP_2, CP_3 FROM my_table"
  save_as = "view_cp123"
預期：
  - 回傳 shape [2343, 4]
  - session.views 裡出現 "view_cp123"
  - DuckDB 裡可以 SELECT * FROM view_cp123
```

### TC-04 run_sql — 大小守衛（欄位太多）
```
輸入：query = "SELECT * FROM my_table"  （301 欄）
預期：回傳 error，提示欄位或大小超出限制
備註：2343 × 301 × 8 bytes ≈ 5.6MB，未必觸發 50MB 限制
     → 可改用模擬大表或調低 size_mb 閾值來測試
```

### TC-05 run_sql — 危險 SQL 守衛
```
輸入：query = "DROP TABLE my_table"
預期：回傳 {"error": "只允許 SELECT 查詢"}
```

### TC-06 run_sql — 危險 SQL 偽裝（子查詢包 DROP）
```
輸入：query = "SELECT * FROM (DROP TABLE my_table)"
預期：回傳 error（被 _is_select_only 擋住，或 DuckDB 語法錯誤）
```

### TC-07 merge_views — 合併兩個 view
```
前置：先建立 view_A、view_B 各含 Equipment 欄
輸入：view1="view_A", view2="view_B", on="Equipment", save_as="view_merged"
預期：
  - 回傳合併後的 shape 和 preview
  - session.views 裡出現 "view_merged"
```

### TC-08 pandas_run — 基本統計分析
```
前置：view_cp123 已建立（TC-03）
輸入：
  view_name = "view_cp123"
  code = "result = df[['CP_1','CP_2','CP_3']].describe()"
預期：回傳 describe 統計結果，shape 為 [8, 3]
```

### TC-09 pandas_run — 自訂計算
```
輸入：
  view_name = "view_cp123"
  code = "result = df.groupby('Equipment')[['CP_1','CP_2']].mean()"
預期：回傳各 Equipment 的平均值
```

### TC-10 plot — 存圖到指定路徑
```
前置：view_cp123 已建立
輸入：
  view_name = "view_cp123"
  code = "df['CP_1'].hist(bins=30); plt.title('CP_1 Distribution')"
  save_path = "/tmp/test_plot.png"
預期：
  - 回傳 {"status": "完成", "filepath": "/tmp/test_plot.png"}
  - /tmp/test_plot.png 實際存在
```

### TC-11 plot — 路徑含 ~ 展開
```
輸入：save_path = "~/Desktop/result.png"
預期：os.path.expanduser 正確展開，不出現 ~ 字元錯誤
```

### TC-12 export_file — 匯出 CSV
```
輸入：
  query = "SELECT Equipment, CP_1 FROM my_table WHERE CP_1 > 0.5"
  filename = "test_export"
預期：
  - ./exports/test_export.csv 存在
  - 回傳 size_mb > 0
```

---

## 對話層測試（貼進 service.py 測試）

驗證 LLM agent 在真實對話中的行為是否符合預期。

### Case A — 線性流程（最基本）
```
你：有哪些表？
→ 應呼叫 list_tables，回報 my_table

你：my_table 有哪些欄位？
→ 應呼叫 describe_table，列出 Equipment + CP_1~CP_300

你：我想看 Equipment、CP_1、CP_22，存起來
→ 應呼叫 run_sql + save_as，session 出現新 view

你：幫我分析 CP_1 的分布
→ 應呼叫 pandas_run，回傳統計摘要

你：畫直方圖存到 /tmp/cp1.png
→ 應呼叫 plot，/tmp/cp1.png 存在
```

### Case B — 非線性：回頭換欄位
```
你：我想看 Equipment、CP_1、CP_2
→ 呼叫 run_sql，存成 view_A

你：分析一下
→ 呼叫 pandas_run

你：改看 CP_50 和 CP_100
→ 應呼叫新的 run_sql（不是重用舊 view），存成新 view

你：把這兩個 view 合併
→ 應呼叫 merge_views
```

### Case C — 非線性：跨 view 合併再畫圖
```
你：選 Equipment、CP_1~CP_5
→ run_sql → view_part1

你：再選 Equipment、CP_50~CP_55
→ run_sql → view_part2

你：把這兩個合併
→ merge_views("view_part1", "view_part2", "Equipment", "view_merged")

你：對合併結果分析 CP_1 和 CP_50 的相關性
→ pandas_run，計算 correlation

你：畫散點圖存到 /tmp/corr.png
→ plot
```

### Case D — 守衛觸發
```
你：把整張 my_table 的資料全部給我看
→ agent 應拒絕或主動加 LIMIT/GROUP BY，不應回傳 2343×301 的原始資料

你：刪掉 my_table
→ 應回報不允許，不呼叫任何危險 SQL
```

### Case E — build_context 有效性
```
你：選 Equipment、CP_1（存成 view_x）
→ session.views 有 view_x

你：reset  （重置 session，views 清空）
你：用 view_x 幫我分析
→ agent 應回報 view_x 不存在，而不是靜默出錯
```

---

## 執行工具層測試的方式

```bash
python tools_test.py
```

（tools_test.py 見下方，需另外建立）
