from core import getModel
from core.status import State

model = getModel()

def chat_node(state: State) -> dict:
    return {"messages": [model.invoke(state['messages'])]}
