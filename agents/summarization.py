from string import Template

from langchain_core.messages import RemoveMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.message import REMOVE_ALL_MESSAGES

from agents.state import State
from agents.engine import get_model


KEEP_RECENT_MESSAGE_COUNT = 10

SYSTEM_CHINESE_PROMPT = Template(
    "你是一個資料分析助理系統裡負責「壓縮對話歷史」的執行者。\n"
    "\n"
    "# 你的職責邊界\n"
    "以下是這個對話裡比較早之前的內容,因為太長需要濃縮,你要把它整理成一段精簡的摘要,\n"
    "取代原本冗長的內容,讓後續的任務還能繼續依賴這些資訊,不會因為濃縮而遺失重要細節。\n"
    "\n"
    "# 濃縮原則\n"
    "\n"
    "1. 任何精確、可識別的具體內容(例如名稱、路徑、數值、代號這類一旦改寫就等於失真的資訊),\n"
    "   一律逐字保留,不要用同義詞或概略的說法取代。\n"
    "2. 只有籠統的敘述、過程性的對話語氣(例如使用者原始問句的措辭細節、\n"
    "   中間反覆確認的過程),才可以濃縮或省略。\n"
    "3. 拿不準某段內容算不算「精確、可識別」,就傾向保留,不要為了精簡而冒著遺失關鍵資訊的風險。\n"
    "\n"
    "# 要濃縮的對話內容\n"
    "$conversation_text\n"
)


def summarization(state: State, config: RunnableConfig) -> dict:

    messages = state["messages"]
    recent_messages = messages[-KEEP_RECENT_MESSAGE_COUNT:]
    older_messages = messages[:-KEEP_RECENT_MESSAGE_COUNT]

    conversation_text = "\n".join(
        f"{message.type}: {message.content}" for message in older_messages
    )
    system_prompt = SYSTEM_CHINESE_PROMPT.substitute(
        conversation_text=conversation_text,
    )
    summary_response = get_model().invoke([
        {"role": "system", "content": system_prompt}
    ])

    update = {
        "messages": [
            RemoveMessage(id=REMOVE_ALL_MESSAGES),
            summary_response,
            *recent_messages,
        ]
    }
    return update
