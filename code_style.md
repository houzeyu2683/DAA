# Code Style

從 `agents/planning.py` 的重寫歸納出來的風格慣例，之後其他檔案盡量比照。

## 命名

- 常數/模板名稱用完整拼出來的英文詞，不用縮寫代碼。例如 `SYSTEM_CHINESE_PROMPT`，不用 `SYSTEM_PROMPT_ZH` 這種帶語言代碼後綴的縮寫。

## 多行字串模板

- 需要 `$placeholder` 之後才填值（例如 system prompt）的情況，用 `string.Template` 包住**並列的一般字串字面量**（每行一個字串、結尾手動加 `\n`），不用三引號字串，也不用 f-string。

  ```python
  SYSTEM_CHINESE_PROMPT = Template(
      "第一行...\n"
      "第二行...$placeholder\n"
  )
  ```

- 不用 f-string 做這種模板，因為 f-string 裡的 `{變數}` 會在該行程式碼執行的當下立即求值，要求變數當時就已經存在於作用域內，這會強迫模板必須寫在變數已存在的地方（例如搬進函式內部），破壞了模板可以留在模組層級當常數的彈性。`$placeholder` 是純文字，不會被立即求值，才能留在模組最外層、等 `.substitute()` 呼叫時才需要真正的值。
- 相鄰字串字面量之間**絕對不能有逗號**——一有逗號就會變成 tuple 而不是字串接續，這是最容易犯的錯。

## 函式內部：拆出具名中間變數，不要一路 inline 到底

不要把整串呼叫鏈一路 inline 寫到 `return`，改成每個有意義的中間結果都給一個名字，讓函式讀起來像逐步交代發生了什麼事：

```python
prompt_request = [
    {"role": "system", "content": system_prompt},
    *state["messages"],
]
promt_response = planning_agent.invoke(prompt_request)

tasks = promt_response["tasks"]
index = -1
return {"tasks": tasks, "index": index}
```

而不是：

```python
result = planning_agent.invoke([
    {"role": "system", "content": system_prompt},
    *state["messages"],
])
return {"tasks": result["tasks"], "index": -1}
```

## 讀取 config 值

- 之後會被當成獨立語意單位使用的值（例如 `session_workspace`、`database_path`），各自拆成一個變數。
- 只是要立刻加工成另一種形狀、不需要保留原始值的（例如 `table_names` 這個 list 要馬上轉成多行文字），可以直接在推導式裡讀 `config["configurable"]["table_names"]`，不用先存一個中間變數再處理。

## 註解

- 預設不寫註解。只有在解釋「為什麼」而且不容易從程式碼本身看出來時才加，例如：

  ```python
  planning_agent = (
      get_model()
      .with_structured_output(Response)
      # 對「網路問題」跟「LLM 偶發性輸出格式錯誤」都有效
      .with_retry(stop_after_attempt=3)
  )
  ```

  這裡加註解是因為 `with_retry` 能處理的失敗類型不容易從呼叫本身看出來，值得說明一句。
