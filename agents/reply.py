from langchain_core.runnables import RunnableConfig

from agents.state import State
from agents.engine import get_model


SYSTEM_PROMPT_ZH = (
    "你是一個資料分析助理系統裡負責「回覆使用者」的執行者,是整個流程的最後一站。\n"
    "\n"
    "# 你的職責邊界\n"
    "根據目前對話裡已經有的所有資訊——可能是前面 data/analysis/chart/summary 執行完累積下來的結果,"
    "也可能使用者的問題本來就能直接從對話回答、不需要額外資訊——整理成一段自然、口語化的回覆,直接回答使用者。\n"
    "\n"
    "不需要呼叫任何工具,也不需要重新查詢資料庫或執行分析。如果現有對話裡的資訊不足以回答,那代表規劃階段"
    "應該要多排一個任務去取得資訊,不是你現在該做的事,你只負責把已經有的結果組織成回覆。\n"
    "\n"
    "# 執行原則\n"
    "\n"
    "1. 用自然的口吻回覆,不要複製貼上前面 summary 產生的正式報告格式,要讀起來像在跟使用者對話。\n"
    "2. 如果前面的過程有產生圖片,提醒使用者圖片的存放位置,讓他們知道去哪裡找。\n"
    "3. 如果前面的過程顯示失敗或查不到結果(例如資料庫不存在、工具執行出錯),"
    "要誠實告訴使用者發生了什麼問題,絕對不能自己編造一個看起來合理的答案。\n"
)


def reply(state: State, config: RunnableConfig) -> dict:

    result = get_model().invoke([
        {"role": "system", "content": SYSTEM_PROMPT_ZH},
        *state["messages"],
    ])

    return {"messages": [result]}
