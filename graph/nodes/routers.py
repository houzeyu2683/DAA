from core.state import State

def task_executing(state: State) -> str:
    """action_planning 後，依任務規劃決定下一個要執行的節點。"""
    # TODO: implement
    ...
    return state['tasks'][0]['agent']


