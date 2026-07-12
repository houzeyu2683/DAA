from langgraph.graph import add_messages
from typing import TypedDict, Annotated, List, Dict
from operator import add


class State(TypedDict):
    messages: Annotated[List, add_messages] # 聊天訊息
    intent: str # 用戶的意圖
    tasks: List # Agent 要執行的任務
    tables: List # 執行任務的中保存的表格名稱放這邊
    charts: List # 執行任務的圖表路徑放在這邊
    history: list # 紀錄每個步驟做的事情

