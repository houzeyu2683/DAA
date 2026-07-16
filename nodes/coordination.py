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
MODEL_NAME = os.environ["MODEL_NAME"]
MODEL_URL = os.environ["MODEL_URL"]
API_KEY = os.environ["API_KEY"]
model = ChatOpenAI(
    model=MODEL_NAME,
    temperature=0,
    base_url=MODEL_URL,
    api_key=API_KEY,
)


class CoordinationState(MessagesState):
    next: str


COORDINATION_SYSTEM_PROMPT = (
    "你是資料分析總指揮，負責協調三位專家，滿足用戶的資料分析需求：\n"
    "- data：資料載入專家，把用戶數據寫入資料庫，確保用戶原始數據不會受到任何編輯。\n"
    "- analysis：統計分析專家，對已存在於資料庫中的表做統計檢定，統計結果也會另外保存在資料庫中。\n"
    "- chart：視覺化分析師，根據用戶數據、統計結果、進行資料視覺化。\n"
    "\n\n"
    "工作區路徑(workspace)：{workspace}\n"
    "本次任務中所有資料庫、統計結果表、圖表輸出，都必須放在這個工作區底下，"
    "除非用戶另有明確指示不同路徑。"
    "\n\n"
    "讀取資料 → 統計分析 → 視覺化，是常見流程，但不是固定流程，"
    "你必須根據目前的對話紀錄自行判斷：\n"
    "1. 只選擇這次任務真正還需要的專家，不要選擇用不到的專家。\n"
    "2. 如果某個步驟先前已經完成(例如用戶數據已寫入資料庫、或統計結果已存在)，"
    "不要重複執行，除非用戶明確要求重做。\n"
    "3. 如果三位專家該做的事情都已經完成，選擇 summary 做最後總結報告。\n"
    "4. 如果用戶的問題跟資料分析、統計、視覺化任務無關，或是你自己就能直接回答、"
    "不需要呼叫任何專家，選擇 reply，並把要回覆用戶的內容寫在 reply 欄位。\n"
    "\n"
    "只能從 'data'、'analysis'、'chart'、'summary'、'reply' 五個選項中選一個，"
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

def coordination_node(state: CoordinationState, config: RunnableConfig) -> dict:
    messages = state["messages"]
    if not _check_system_prompt(messages):
        content = COORDINATION_SYSTEM_PROMPT.format(
            workspace=config["configurable"]['workspace']
        )
        messages = [SystemMessage(content=content)] + messages

    # messages = _ensure_system_prompt(state["messages"], COORDINATION_SYSTEM_PROMPT)
    task = model.with_structured_output(Task, method="function_calling").invoke(messages)
    update = {"next": task['next']}
    if task['next'] == "reply":
        update["messages"] = [AIMessage(content=task['reply'] or "")]
    return update


# def route_after_coordination(state: CoordinationState) -> str:
#     return state["next"]


