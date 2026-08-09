# agents/tables 共同慣例

`data.py`、`analysis.py`、`chart.py`、`summary.py` 這幾個節點檔案,除了各自的職責邊界不同,
底層的錯誤處理跟工具寫法是統一的慣例,新增檔案時比照辦理。

## 兩層錯誤防禦

每個節點的 agent(`data_agent`、`analysis_agent`、`chart_agent`、`summary_agent`)都套用
`ToolErrorMiddleware`,搭配一個節點自己的 `on_tool_error`:

```python
def on_tool_error(exception: Exception, request) -> str:
    tool_name = request.tool_call["name"]
    tool_args = request.tool_call["args"]
    return f"{tool_name}({tool_args}) 失敗: {type(exception).__name__}: {exception}"


xxx_agent = create_agent(
    get_model(),
    tools=[...],
    middleware=[ToolErrorMiddleware(on_tool_error)],
)
```

節點函式(`data`/`analysis`/`chart`)外層另外包一層 `try/except Exception`:

```python
try:
    prompt_response = xxx_agent.invoke(prompt_request)
except Exception as exception:
    update = {
        "messages": [
            {
                "role": "assistant",
                "content": (
                    f"失敗: {type(exception).__name__}: {exception}"
                ),
            }
        ],
        "error": True
    }
    return update
```

這兩層負責的範圍不同,**都要留著,不能互相取代**:

- **`on_tool_error`**:只處理「工具執行期間」拋出的例外(例如 `duckdb.Error`)。
  它會把例外轉成 `ToolMessage(status="error")`,讓 agent 在同一輪 ReAct loop 裡
  看到錯誤內容、有機會自己修正重試。
- **外層 `try/except`**:接住 `on_tool_error` 範圍以外的所有意外
  (例如 LLM API 呼叫本身失敗、網路問題),是最後一道防線,讓整個節點優雅地
  降級成 `{"error": True, ...}`,不會讓例外一路往外炸穿整個 workflow。

兩者理論上有一點重疊(如果 `on_tool_error` 曾經回傳 `None`,例外會被外層接住),
但目前每個 `on_tool_error` 都無條件回傳字串,不會走到那條退化路徑。

`GraphBubbleUp`(以及 `GraphInterrupt` 等子類別,LangGraph 用來做 interrupt、
parent command 的控制流訊號)會被 `ToolErrorMiddleware` 直接放行,不會經過
`on_tool_error`。目前專案沒用到 `interrupt()`,但如果未來要加
human-in-the-loop 功能,外層 `except Exception` 需要額外排除
`GraphBubbleUp`(例如 `except GraphBubbleUp: raise` 放在前面),否則會誤吃掉
控制流訊號。

## `parse_characters`

每個工具函式的字串參數,第一步都先過一次 `parse_characters`,避免 LLM
把參數多包一層雙重引號當輸入:

```python
def parse_characters(characters: str) -> str:
    """避免雙重引號的參數當作輸入"""

    return characters.strip('"').strip("'")
```

目前 `data.py`/`analysis.py`/`chart.py` 各自有一份重複的定義,還沒抽成共用模組
(暫時的決定,之後有需要再共用)。

## DuckDB 連線一律用 `with`

不手動呼叫 `.close()`,一律用 context manager,確保中途出錯連線也會被關閉:

```python
with duckdb.connect(database_path, read_only=True) as connection:
    ...
```

寫入資料庫的工具才需要 `read_only=False`(預設值),單純查詢/讀取一律加
`read_only=True`。

## 跨任務的上下文:過濾歷史訊息,不用獨立欄位

`data`/`analysis`/`chart` 執行前,都會把 `state["messages"]` 裡目前為止的
`AIMessage`(每個任務結束時留下的那句回報)過濾出來,一併傳進自己的
`xxx_agent.invoke(...)`,讓這個任務能看到前面任務做過什麼、產生了什麼:

```python
from langchain_core.messages import AIMessage

previous_messages = [
    message for message in state["messages"]
    if isinstance(message, AIMessage)
]
prompt_request = {
    "messages": [
        {"role": "system", "content": system_prompt},
        *previous_messages,
    ]
}
```

早期版本曾經另外設計一個 `state["feedback"]`(`Annotated[list[str], operator.add]`)
欄位來做同一件事,但這個 reducer 只能加、沒辦法在新一輪對話開始時重置,導致
跨輪次的舊回報一直洩漏進新一輪的任務裡。後來發現 `state["messages"]` 本身已經
夠乾淨(每個節點只留最後一句回報,不含 tool_call 細節),直接過濾使用即可,
不需要額外維護一個欄位,已經拿掉 `feedback`。

如果之後對話輪數變多、訊息持續累積,由 `orchestration.py` 統一判斷
`len(state["messages"])` 是否超過門檻,超過就先繞去 `agents/summarization.py`
的 `summarization` 節點壓縮成摘要,不需要每個節點各自處理。

`summary.py` 是例外——它需要看到完整對話(包含使用者原始問句)才能寫報告,
所以維持傳整個 `state["messages"]`,不做 `AIMessage` 過濾。

## System prompt 上下文欄位

每個節點的 system prompt 都用 `Template` + 串接字串(見專案根目錄
`code_style.md`),固定包含這些上下文欄位:

- `$session_workspace` — 工作目錄
- `$database_path` — 資料庫位置
- `$table_names` — 資料表名稱清單
- 這次要執行的任務(欄位名稱目前不完全統一,`data.py`/`analysis.py` 用
  `$current_task`,`chart.py` 用 `$action`)
