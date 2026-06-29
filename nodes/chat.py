from core.functions import getModel
from core.status import State

model = getModel()

def chat_node(state: State) -> dict:
    response = model.invoke(state['messages'])
    return {"messages": [response]}
