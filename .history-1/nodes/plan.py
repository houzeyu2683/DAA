from typing import Literal, TypedDict
from langchain_core.messages import SystemMessage, filter_messages, AIMessage


from core.functions import getModel
from core.status import State

model = getModel()

class Task(TypedDict):
    type: Literal["sql", "pd", "stats", "plot", "report"]
    description: str

class TaskList(TypedDict):
    tasks: list[Task]

_system = SystemMessage(content="""你是一個任務規劃器。
根據用戶的需求，將任務拆解成有序的步驟，每個步驟指定一個 type ，
每個步驟只會執行一次操作，也就是一次指令，如果需要多個指令才可以完成，
就要拆成多個任務。

可用的 type：
- sql：從資料庫查詢、篩選、排序、分組、取 TOP N 等，能用 SQL 完成的操作都用這個
- pd：只有 SQL 無法完成的複雜資料轉換才用這個
- stats：統計分析（ANOVA、t-test 等）
- plot：視覺化、畫圖
- report：整理並輸出分析結果

輸出 tasks 列表，按執行順序排列。""")

_planner = model.with_structured_output(TaskList)

def plan_node(state: State) -> dict:
    conversation = filter_messages(state['messages'], include_types=["human", "ai"])
    response = _planner.invoke([_system] + conversation[-6:])
    tasks = response["tasks"]
    content = "\n".join(
        f"{i+1}. [{t['type']}] {t['description']}" for i, t in enumerate(tasks)
    )
    message = AIMessage(content=f"我規劃了以下步驟：\n{content}")
    return {"tasks": tasks, "messages": [message]}
