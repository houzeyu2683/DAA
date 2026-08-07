from typing import TypedDict, Literal

from langchain_core.runnables import RunnableConfig
from langgraph.types import Command, interrupt
from langgraph.graph import END

from .state import State, Task
from utilities import get_model
from prompts.replanning import SYSTEM_PROMPT_ZH


class Response(TypedDict):
    status: Literal["continue", "done", "error"]
    reason: str  # status 為 error 時,顯示給使用者看,說明計畫為什麼需要調整
    proposal: list[Task]  # status 為 error 時才需要,修改後的任務清單(只放還沒執行的部分)


replanning_agent = (
    get_model()
    .with_structured_output(Response)
    .with_retry(stop_after_attempt=3)
)


def replanning(state: State, config: RunnableConfig) -> Command:
    # 1. 準備 system prompt 要用的上下文:資料庫位置、表名、目前完整的任務清單
    database_path = config["configurable"]["database_path"]
    table_names = config["configurable"]["table_names"]
    table_names_text = "\n".join(f"- {name}" for name in table_names)
    tasks_text = "\n".join(
        f"{i}. [{task['direction']}] {task['action']}"
        for i, task in enumerate(state["tasks"])
    )

    system_prompt = SYSTEM_PROMPT_ZH.substitute(
        database_path=database_path,
        table_names=table_names_text,
        tasks=tasks_text,
        index=state["index"],
    )

    # 2. 呼叫模型,讀 state["messages"](裡面有剛剛那個 task 的執行結果),判斷 status
    result = replanning_agent.invoke([
        {"role": "system", "content": system_prompt},
        *state["messages"],
    ])

    # 3-a. 使用者的需求已經完整處理完了,跳去 reply 收尾
    if result["status"] == "done":
        return Command(goto="reply", update={"status": "done"})

    # 3-b. 計畫維持不變,直接接著跑清單裡下一個 task
    if result["status"] == "continue":
        next_index = state["index"] + 1
        next_task = state["tasks"][next_index]
        return Command(
            goto=next_task["direction"],
            update={"index": next_index, "status": "continue"},
        )

    # 3-c. status == "error":計畫需要調整,用 interrupt() 暫停,把原因跟建議的新計畫
    #      攤給使用者看,讓使用者決定要不要接受
    decision = interrupt({
        "reason": result["reason"],
        "proposal": result["proposal"],
    })

    # 使用者不接受新計畫 → 這輪直接結束,使用者之後自己重打訊息會重新從 planning 開始
    if decision != "accept":
        return Command(goto=END)

    # 使用者接受 → 把已完成的 task(保留)+ 建議的新 task 接成新的完整清單,繼續往下跑
    new_tasks = state["tasks"][: state["index"] + 1] + result["proposal"]
    next_index = state["index"] + 1
    next_task = new_tasks[next_index]

    return Command(
        goto=next_task["direction"],
        update={"tasks": new_tasks, "index": next_index, "status": "continue"},
    )
