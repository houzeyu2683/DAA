from typing import Optional, List, Dict, TypedDict

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from core import get_model
from core.state import State
# 處理資料查詢或挑選欄位；查詢/挑選完之後，必須把結果另存成一張新表，並提供這張表的摘要。
# 正確範例：

# 輸入：「讀取 '.data/frame.csv' 表，針對 Equipment 與包含 _wat 的欄位進行 ANOVA 分析，
# 找出差異最大的前五個，畫出對應的 box‑chart 圖，並提供報告。」

# 輸出：{
#     "tasks": [
#         {
#             'agent': 'DATA',
#             'instruction': '讀取 '.data/frame.csv' 表，存進指定的資料庫'
#         },
#         {
#             'agent': 'STATS',
#             'instruction': '讀取資料庫的表格，針對 Equipment 與包含 _wat 的欄位進行 ANOVA 分析，找出差異最大的前五個'
#         }
#     ]
# }


_SYSTEM_TEMPLATE = """
你是一個任務規劃者。理解用戶想做什麼之後，把工作分派給以下三個 Agent。

規則：

每個 Agent 都有負責的工作範圍，權限劃分清楚

DATA Agent
負責資料處理。讀取用戶提供的資料並存進用戶的個人資料庫。
不能查詢或過濾資料，只負責將用戶原始資料存入資料庫。

STATS Agent
讀取 DATA Agent 存好的表，查詢或選擇適當的欄位，套用合適的統計方法，執行統計分析。
分析結果是表格則必須另存成一張新表，輸出前檢查用戶是否有**篩選統計結果的需求**，
沒有則預設篩選統計差異最大的前 20 筆結果。
責任重大，會搭配對應的 MCP 工具來讓 Agent 使用，欄位挑選、統計方法、
結果過濾都會一次在這個工具中完成。

CHART Agent
負責資料視覺化。讀取 DATA Agent 存好的表，必要時搭配 STATS Agent 的結果，
用合適的工具產生圖表，圖案必須另存新檔。
責任重大，也會搭配對應的 MCP 工具來讓 Agent 使用，欄位挑選、畫圖、會一次在這個工具中完成。

REPORT Agent
根據先前的工作，進行總結跟報告。
不管用戶有沒有提出要簡短報告，都必需要在最後給出一個總結跟報告。

每個 Agent 最多只能出現一次。針對真正需要的每個 Agent，寫一句清楚、自包含的指令——這句指令會直接交給該 Agent 去搭配工具執行，不會再做額外的意圖解讀。
如果某個 Agent 這次用不到，就把它的 instruction 設成 null。

輸出格式
```JSON
{
    'tasks': [
        {
            'agent': 'DATA',
            'instruction': '...'
        },
        {
            'agent': 'STATS',
            'instruction': '...'
        },
        {
            'agent': 'CHART',
            'instruction': '...'
        },
        {
            'agent': 'REPORT',
            'instruction': '...'
        }                        
    ]
}
```

用繁體中文來描述 instruction 的內容
"""

class Task(TypedDict):
    agent: str
    instruction: Optional[str]

class Plan(TypedDict):
    tasks: List[Task]

_max_try = 5
_try = 0

def action_planning(state: State, config: RunnableConfig) -> dict:
    """理解用戶意圖，將工作拆解成任務，分派給 DATA / STATS / CHART Agent 執行。"""
    model = get_model().with_structured_output(Plan)
    conversation = [SystemMessage(_SYSTEM_TEMPLATE)] + state["messages"]
    while _try < _max_try:
        try:
            planning = model.invoke(conversation)
        except:
            continue
        break
    tasks = planning['tasks']
    for task in tasks:
        print(task)
        continue
    return {"tasks": tasks}


