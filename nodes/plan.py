from typing import Literal
from langchain_core.messages import SystemMessage, filter_messages, AIMessage
from pydantic import BaseModel

from core.functions import getModel
from core.status import State

model = getModel()

class Task(BaseModel):
    type: Literal["sql", "pd", "stats", "plot", "report"]
    description: str

class TaskList(BaseModel):
    tasks: list[Task]

_system = SystemMessage(content="""你是一個任務規劃器。
根據用戶的需求，將任務拆解成有序的步驟，每個步驟指定一個 type。

可用的 type：
- sql：從資料庫查詢或篩選資料
- pd：用 pandas 做資料處理、轉換
- stats：統計分析（ANOVA、t-test 等）
- plot：視覺化、畫圖
- report：整理並輸出分析結果

輸出 tasks 列表，按執行順序排列。""")

_planner = model.with_structured_output(TaskList)

def plan_node(state: State) -> dict:
    conversation = filter_messages(state['messages'], include_types=["human", "ai"])
    response = _planner.invoke([_system] + conversation[-6:])
    tasks = [task.model_dump() for task in response.tasks]
    content = "\n".join(
        f"{i+1}. [{t['type']}] {t['description']}" for i, t in enumerate(tasks)
    )
    message = AIMessage(content=f"我規劃了以下步驟：\n{content}")
    return {"tasks": tasks, "messages": [message]}
