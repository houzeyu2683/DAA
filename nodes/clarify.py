from langchain_core.messages import SystemMessage, AIMessage
from core.functions import getModel
from core.status import State

model = getModel()

_system = SystemMessage(content="""用戶的需求不夠明確。
請根據對話內容，提出一個具體的追問，幫助釐清用戶真正想要什麼。
只問一個問題，簡短清楚。""")

def clarify_node(state: State) -> dict:
    response = model.invoke([_system] + state['messages'])
    return {"messages": [AIMessage(content=response.content)]}
