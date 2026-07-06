from langchain_core.messages import SystemMessage, AIMessage
from core import getModel
from core.status import State

model = getModel()

content = """用戶的需求不夠明確。
請根據對話內容，提出一個具體的追問，幫助釐清用戶真正想要什麼。
只問一個問題，簡短清楚。"""

# _system = SystemMessage(content)

def clarify_node(state: State) -> dict:
    response = model.invoke([SystemMessage(content)] + state['messages'])
    print(response)
    return {"messages": [response]}
