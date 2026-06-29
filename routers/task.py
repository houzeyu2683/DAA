from core.status import State

def task_router(state: State) -> str:
    if not state['tasks']:
        return "human"
    return state['tasks'][0]['type'] # 只看當前的就好
