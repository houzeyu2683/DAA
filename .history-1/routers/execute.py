from core.status import State


def execute_router(state: State) -> str:

    '''
    state.tasks:
    [
        {'type': 'sql', 'description': '從資料庫中選擇欄位 Equipment 和 CP_50-100 的資料'}, 
        {'type': 'stats', 'description': '對選擇出的資料執行 ANOVA 分析，以找出差異最大的三個機器'}, {'type': 'pd', 'description': '根據 ANOVA 分析結果，篩選出差異最大的三個機器的資料'}, 
        {'type': 'plot', 'description': '使用篩選出的資料繪製箱型圖 (box chart)，展示機器和 CP 之間的分佈'}
    ]
    '''
    tasks = state["tasks"]
    if not tasks:
        return "report"
    return tasks[0]['type']
