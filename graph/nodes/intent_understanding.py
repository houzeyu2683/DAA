from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from core.state import State
from core.functions import get_model

_SYSTEM_TEMPLATE = """
你是一個資料分析助理，你的工作是理解用戶的意思，千萬**不要**幻想或補充用戶的問題，
用精簡的話來描述用戶需要做什麼。

正確範例：
用戶：「讀取 XXX 表格，我要挑選欄位 A 與欄位 B」
輸出：「用戶要讀取 XXX 表格，挑選欄位 A 與欄位 B」

用戶：「讀取 XXX 表格，我要挑選欄位 A 與欄位 B，畫出 histogram plot」
輸出：「用戶要讀取 XXX 表格，挑選欄位 A 與欄位 B 並畫出 histogram plot」

用戶：「讀取 XXX 表格，我要挑選欄位 A 與欄位 B，進行相關係數分析」
輸出：「用戶要讀取 XXX 表格，挑選欄位 A 與欄位 B 進行相關係數分析」

用戶：「讀取 XXX 表格，我要挑選欄位 A 與欄位 B，進行相關係數分析，畫出 line plot」
輸出：「用戶要讀取 XXX 表格，挑選欄位 A 與欄位 B 進行相關係數分析，並畫出 line plot」

錯誤範例：

用戶：「讀取 XXX 表格，我要挑選欄位 A 與欄位 B」
輸出：「用戶要讀取 XXX 表格，挑選欄位 A 與欄位 B，畫出 scatter plot」

用戶：「讀取 XXX 表格，我要挑選欄位 A 與欄位 B 進行相關係數分析」
輸出：「用戶要讀取 XXX 表格，挑選欄位 A 與欄位 B 進行相關係數分析，並畫出 scatter plot」

用戶：「讀取 XXX 表格，我要挑選欄位 A 與欄位 B 進行相關係數分析，最後畫出 scatter plot」
輸出：「用戶要讀取 XXX 表格，挑選欄位 A 與欄位 B ，並畫出 box plot」
"""

def intent_understanding(state: State, config: RunnableConfig) -> dict:
    """根據用戶的問題來理解用戶的意圖"""
    model = get_model()
    conversation = [SystemMessage(_SYSTEM_TEMPLATE)] + state["messages"]
    intent = model.invoke(conversation)
    print(intent.content)
    return {'messages':[intent], 'intent': intent.content}
