from core.status import State

def intent_router(state: State) -> str:
    return state['intent']['type']
