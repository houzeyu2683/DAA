from core.status import State
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import filter_messages
import json
from langchain_core.messages import HumanMessage
from langchain_core.messages import SystemMessage, AIMessage
from core.functions import getModel

model = getModel()

def report_node(state: State, config: RunnableConfig) -> dict:
    stats = state["stats"]
    conversation = filter_messages(state["messages"], include_types=["human", "ai"])
    stats_str = json.dumps(stats, ensure_ascii=False, indent=2)
    human = HumanMessage(content=f"以下是這次分析的統計結果，請根據這些數字撰寫總結：\n{stats_str}")

    system = SystemMessage(content="""你是一個資料分析報告撰寫者。
    根據統計結果和分析過程，用繁體中文撰寫一份清楚的總結報告。
    說明分析了什麼、結果是否顯著、以及重要發現。
    """)

    response = model.invoke([system] + conversation[-6:] + [human])
    return {
        "tasks": state["tasks"][1:],
        "messages": [response]
    }



