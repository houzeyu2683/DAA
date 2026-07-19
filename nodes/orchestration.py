import os
from typing import Literal, Optional, TypedDict
from dotenv import load_dotenv
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, MessagesState, START, END
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig


load_dotenv()
model_name = os.environ["MODEL_NAME"]
model_url = os.environ["MODEL_URL"]
model_key = os.environ["MODEL_KEY"]
model = ChatOpenAI(
    model=model_name,
    temperature=0.2,
    base_url=model_url,
    api_key=model_key,
)


class OrchestrationState(MessagesState):
    next: str


ORCHESTRATION_SYSTEM_PROMPT = (
    "你是資料分析總指揮，負責協調三位專家，滿足用戶的資料分析需求：\n"
    "- data：資料載入專家，把用戶數據寫入資料庫，確保用戶原始數據不會受到任何編輯。\n"
    "- analysis：統計分析專家，對已存在於資料庫中的表做統計檢定，統計結果也會另外保存在資料庫中。\n"
    "- chart：視覺化分析師，根據用戶數據、統計結果、進行資料視覺化。\n"
    "\n\n"
    "工作區路徑(workspace)：{workspace}\n"
    "本次任務中所有資料庫、統計結果表、圖表輸出，都必須放在這個工作區底下，"
    "除非用戶另有明確指示不同路徑。"
    "\n\n"
    "分析流程如下：\n"
    "- 讀取資料 → 統計分析 → 視覺化\n"
    "- 讀取資料 → 視覺化\n"
    "- 讀取資料 → 統計分析\n"
    "錯誤範例：\n"
    "輸入：幫我對某某欄位進行分析\n"
    "輸出：進行分析後畫圖\n\n"
    "輸入：幫我對某某欄位進行畫圖\n"
    "輸出：進行分析後畫圖\n\n"
    "核心觀念：用戶沒有說的行為禁止去執行"
    "你必須根據目前的對話紀錄自行判斷：\n"
    "1. 只選擇這次任務真正還需要的專家，不要選擇用不到的專家。\n"
    "2. 如果某個步驟先前已經完成(例如用戶數據已寫入資料庫、或統計結果已存在)，"
    "不要重複執行，除非用戶明確要求重做。\n"
    "3. 如果三位專家該做的事情都已經完成，選擇 summary 做最後總結報告。\n"
    "4. 如果用戶的問題跟資料分析、統計、視覺化任務無關，或是你自己就能直接回答、"
    "不需要呼叫任何專家，選擇 reply，並把要回覆用戶的內容寫在 reply 欄位。\n"
    "\n"
    "只能從 'data'、'analysis'、'chart'、'summary'、'reply' 五個選項中選一個，"
    "範例: {{'next': 'data', 'reply': '...'}}"
    "作為接下來要交給誰處理。"
)


class Task(TypedDict):
    next: Literal["data", "analysis", "chart", "summary", "reply"]
    reply: Optional[str]


# def _ensure_system_prompt(messages: list, prompt: str) -> list:
#     if messages and getattr(messages[0], "type", None) == "system":
#         return messages
#     return [SystemMessage(content=prompt)] + list(messages)

def _check_system_prompt(messages: list) -> bool:
    if(messages==[]): return False
    if getattr(messages[0], "type") == "system": return True
    return False


ATTEMPT = 3
def orchestration_node(state: OrchestrationState, config: RunnableConfig) -> dict:
    workspace = config["configurable"]['workspace']
    messages = state["messages"]
    if not _check_system_prompt(messages):
        system_prompt = ORCHESTRATION_SYSTEM_PROMPT.format(workspace=workspace)
        messages = [SystemMessage(content=system_prompt)] + messages

    # messages = _ensure_system_prompt(state["messages"], COORDINATION_SYSTEM_PROMPT)
    attempt = 0
    while attempt < ATTEMPT:
        # task = model.with_structured_output(Task, method="function_calling").invoke(messages)
        task = model.with_structured_output(Task, method='json_mode').invoke(messages)
        if task:
            break
        attempt += 1
        continue

    assert attempt!=3, "超過嘗試次數"
    # print(attempt)

    update = {"next": task['next']}
    if task['next'] == "reply":
        update["messages"] = [AIMessage(content=task['reply'] or "")]
    return update


# def route_after_coordination(state: CoordinationState) -> str:
#     return state["next"]


