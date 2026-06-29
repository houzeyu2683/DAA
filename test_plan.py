from pydantic import BaseModel
from core.functions import getModel

model = getModel()

class Task(BaseModel):
    type: str
    description: str

class TaskList(BaseModel):
    tasks: list[Task]

planner = model.with_structured_output(TaskList)

result = planner.invoke("幫我挑出 Equipment 和 CP_50-100 欄位，做 ANOVA 分析，然後畫 box chart")

print(type(result))        # <class 'TaskList'>
print(result.tasks)        # [Task(...), Task(...), ...]

for task in result.tasks:
    print(task.type, "→", task.description)
