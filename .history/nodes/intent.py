from typing import Literal
from langchain_core.messages import SystemMessage, filter_messages
from pydantic import BaseModel

from core.functions import getModel
from core.status import State

model = getModel()

class Intent(BaseModel):
    intent: Literal["chat", "plan", "clarify"]

_classifier = model.with_structured_output(Intent)

_system = SystemMessage(content="""你是一個意圖分類器。
根據用戶的最近幾則訊息，判斷意圖並只回覆以下其中一個詞：
- chat：一般對話、問候、或可以直接回答的問題
- plan：需求明確，包含具體的欄位、分析方式、或圖表類型
- clarify：需求模糊，缺少具體欄位、分析目標、或圖表類型，無法直接執行

範例：
「幫我畫圖」→ clarify（沒有指定欄位或圖表類型）
「幫我分析」→ clarify（沒有指定分析目標）
「幫我畫 Equipment 和 CP_50-100 的 box chart」→ plan
「幫我對 Equipment 做 ANOVA 分析」→ plan
「你好」→ chat

只回覆 chat、plan 或 clarify，不要有其他文字。""")

def intent_node(state: State) -> dict:
    conversation = filter_messages(state['messages'], include_types=["human", "ai"])
    result = _classifier.invoke([_system] + conversation[-4:])
    return {"intent": result.intent}
