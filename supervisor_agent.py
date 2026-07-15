import os
import uuid

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langgraph.checkpoint.memory import InMemorySaver

from data_agent import data_agent
from stats_agent import stats_agent
from chart_agent import chart_agent

load_dotenv()
MODEL_NAME = os.environ["MODEL_NAME"]
MODEL_URL = os.environ["MODEL_URL"]
API_KEY = os.environ["API_KEY"]


@tool
def call_data_agent(instruction: str) -> str:
    """呼叫資料載入專家，處理 CSV 寫入 DuckDB 相關的任務。

    參數:
        instruction: 用自然語言描述要資料載入專家做的事情，需要包含
            CSV 路徑與資料庫路徑，例如「把 A.csv 讀進 B.db」，
            或「檢查 B.db 裡某張表長什麼樣子」。
    """
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    result = data_agent.invoke(
        {"messages": [{"role": "user", "content": instruction}]},
        config,
    )
    return result["messages"][-1].content


@tool
def call_stats_agent(instruction: str) -> str:
    """呼叫統計分析專家，針對已經存在於 DuckDB 資料庫中的表做統計分析(目前為 ANOVA)。

    參數:
        instruction: 用自然語言描述要統計分析專家做的事情，需要包含
            資料庫路徑、表名，以及要分析的類別欄位與數值欄位(可以用明確欄位名稱，
            也可以用欄位名稱規則，例如「所有包含 _id 的欄位」)，
            例如「對 B.db 裡的 XXX 表，針對 minutes_played 欄位與所有包含 _id 的欄位做 ANOVA」。
    """
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    result = stats_agent.invoke(
        {"messages": [{"role": "user", "content": instruction}]},
        config,
    )
    return result["messages"][-1].content


@tool
def call_chart_agent(instruction: str) -> str:
    """呼叫視覺化分析師，讀取統計結果並畫箱型圖(box chart)。

    參數:
        instruction: 用自然語言描述要視覺化分析師做的事情，需要包含
            資料庫路徑、原始資料表名、統計結果表名，以及要看差異最大或最小的前幾筆，
            例如「對 B.db 裡的統計結果表 XXX_anova_YYY，找出差異最大的前 5 筆，畫 box chart」。
    """
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    result = chart_agent.invoke(
        {"messages": [{"role": "user", "content": instruction}]},
        config,
    )
    return result["messages"][-1].content


model = ChatOpenAI(
    model=MODEL_NAME,
    temperature=0,
    base_url=MODEL_URL,
    api_key=API_KEY
)
checkpointer = InMemorySaver()

SUPERVISOR_PROMPT = (
    "你是資料分析總指揮，負責協調三位專家，滿足用戶的資料分析需求：\n"
    "- call_data_agent(資料載入專家)：把 CSV 寫入 DuckDB、檢查資料庫與表的狀態。\n"
    "- call_stats_agent(統計分析專家)：對已存在於資料庫中的表做統計檢定(目前為 ANOVA)。\n"
    "- call_chart_agent(視覺化分析師)：讀取統計結果、畫箱型圖(box chart)。\n"
    "\n"
    "讀取資料 → 統計分析 → 視覺化，是常見流程，但不是固定流程，"
    "你必須根據用戶當下的請求自行判斷：\n"
    "1. 只呼叫這次任務真正需要的專家，不要呼叫用不到的專家。\n"
    "2. 如果某個步驟先前已經完成(例如 CSV 已寫入資料庫、或統計結果已存在)，"
    "不要重複執行，除非用戶明確要求重做。\n"
    "3. 如果用戶要求換參數重跑，只重新呼叫受影響的那幾位專家，"
    "其餘已完成的步驟維持先前的結果，不要重跑。\n"
    "\n"
    "三位專家之間彼此沒有記憶，每一次呼叫都是獨立、無上下文的一次性任務，"
    "只有你記得完整脈絡(例如資料庫路徑、表名、統計結果表名、欄位名稱)。"
    "因此每次呼叫任何一位專家前，都必須在 instruction 裡把這次任務需要的完整資訊寫清楚，"
    "不能假設專家記得你們之前討論過的內容。\n"
    "\n"
    "禁止產生任何程式碼，"
    "完成任務後總結一下呼叫了哪些專家、做了什麼、有哪些關鍵資訊"
    "(例如表名、統計結果表名、圖檔路徑)，以及接下來可能需要做什麼。"
)

tools = [call_data_agent, call_stats_agent, call_chart_agent]
supervisor_agent = create_agent(
    model,
    tools=tools,
    system_prompt=SUPERVISOR_PROMPT,
    checkpointer=checkpointer
)


config = {"configurable": {"thread_id": "supervisor_demo"}}
CSV_PATH = ".data/archive/fifa_world_cup_2026_player_performance.csv"
DB_PATH = ".data/tmp/data_agent_demo/database.db"

question = (
    f"幫我讀取 {CSV_PATH} 檔案，我要針對欄位 'minutes_played' "
    f"以及包含 '_id' 的欄位，進行 ANOVA 分析，"
    f"接著幫我把差異最小的前五個結果找出來，我想用 box-chart 把圖畫出來。"
    f"資料庫路徑是 {DB_PATH}。"
)


if __name__ == "__main__":
    result = supervisor_agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
        config,
    )
    for message in result["messages"]:
        message.pretty_print()
