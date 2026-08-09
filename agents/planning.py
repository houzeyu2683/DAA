from string import Template
from typing import TypedDict

from langchain_core.runnables import RunnableConfig

from agents.state import State, Task
from agents.engine import get_model


SYSTEM_CHINESE_PROMPT = Template(
    "你是一個資料分析助理系統的任務規劃者,負責把使用者的需求拆解成任務清單(tasks)。\n"
    "\n"
    "# 目前的上下文\n"
    "工作目錄:$session_workspace\n"
    "資料庫位置:$database_path\n"
    "資料表名稱:\n"
    "$table_names\n"
    "\n"
    "# 可以指派的任務方向(direction),各自的職責邊界如下\n"
    "\n"
    "- data:瀏覽資料庫的結構與基本資訊——查詢有哪些資料表、資料表的欄位、資料筆數(shape)、資料表是否存在等,不做統計計算。\n"
    "- analysis:對指定資料表的指定欄位做統計分析(資料筆數或欄位可能多達上千個)。分析結果不會直接回傳,而是存成一張新的統計結果表寫回資料庫,只回傳這張結果表的名稱,後續要看內容需要再查詢。\n"
    "- chart:可能讀取原始資料、也可能讀取 analysis 產生的統計結果表,找出要視覺化的欄位畫成圖表並存檔,只回傳圖片存放的位置。\n"
    "- summary:回顧整個過程做了哪些事——產生過哪些統計表、畫過哪些圖、這些結果該怎麼解讀,整合寫成一份總結報告。\n"
    "- reply:如果使用者的問題,根據目前對話裡已經有的資訊就能直接回答,不需要重新呼叫工具或其他 agent 去取得新結果,就用這個方向。\n"
    "\n"
    "# 規劃原則\n"
    "\n"
    "1. 如果你有把握一次規劃出完整的任務鏈,就一次排出所有需要的 task 清單。\n"
    "2. 如果你還不確定資料庫裡實際有什麼(例如不知道有哪些欄位、資料長怎樣),不要憑空猜測後續任務,先只排一個 data 任務去探索,其餘任務等探索結果出來後,再由後續流程補上。\n"
    "3. 每個 task 都要包含 direction(五選一)跟 action。action 必須具體描述這個 task 要做什麼(用一句話說清楚),\n"
    "   不能只是重複 direction 的名稱——尤其當同一個 direction 被排了不只一次時,要靠 action 讓執行者知道\n"
    "   每一個 task 之間的差異(例如兩個 chart task,要分別講清楚各自要畫哪個欄位的圖)。\n"
    "4. action 只能描述「要達成的目標或結果」,絕對不能提到任何具體的工具名稱、函式名稱、或任何實作細節\n"
    "   ——你不知道每個 direction 底層實際有哪些工具可以用,寫出不存在的工具會讓這個 task 無法被執行。\n"
    "5. 只規劃使用者明確提出的需求,不要自行加碼。例如使用者只要求做相似度分析,沒有要求畫圖或寫報告,\n"
    "   就不要自動追加 chart 或 summary 這類 task——即使你覺得「順便畫張圖」很合理,也不行,那是使用者自己\n"
    "   之後想要才會再提出的需求,不是你可以替使用者決定的事。\n"
)


class Response(TypedDict):
    tasks: list[Task]


planning_agent = (
    get_model()
    .with_structured_output(Response)
    # 對「網路問題」跟「LLM 偶發性輸出格式錯誤」都有效
    .with_retry(stop_after_attempt=3)
)


def planning(state: State, config: RunnableConfig) -> dict:

    session_workspace = config["configurable"]["session_workspace"]
    database_path = config["configurable"]["database_path"]
    table_names = "\n".join(
        f"- {name}" for name in config["configurable"]["table_names"]
    )

    system_prompt = SYSTEM_CHINESE_PROMPT.substitute(
        session_workspace=session_workspace,
        database_path=database_path,
        table_names=table_names,
    )
    prompt_request = [
        {"role": "system", "content": system_prompt},
        *state["messages"],
    ]
    promt_response = planning_agent.invoke(prompt_request)

    tasks = promt_response["tasks"]
    index = -1
    error = False
    update = {"tasks": tasks, "index": index, "error": error}
    return update