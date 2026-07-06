from langgraph.graph import (
    StateGraph, 
    START, 
    END
)
from langgraph.checkpoint.memory import MemorySaver
from os import makedirs
from uuid import uuid4
from langgraph.types import Command

# ----- 客制化 -----
from graph.state import State
from graph.nodes import (
    user_question,
    intent_understanding,
    action_planning
)

# ----- 組裝圖 -----
# Node
sketch = StateGraph(State)
sketch.add_node("user_question", user_question)
sketch.add_node("intent_understanding", intent_understanding)
sketch.add_node("action_planning", action_planning)
# Edge
sketch.add_edge(START, "user_question")
sketch.add_edge("user_question", "intent_understanding")
sketch.add_edge("intent_understanding", "action_planning")
# sketch.add_edge("intent_understanding", END)
# Compile
workflow = sketch.compile(checkpointer=MemorySaver())
workflow.get_graph().draw_png('workflow.png')

if __name__ == '__main__':

    """
    初始化狀態與設定
    """
    ##  用戶登入
    user_id = 'G72602'
    ##  分配一個 thread 用來表示這次的談話
    thread_id = uuid4().hex[:4]
    ##  新增一個空間用來存放個人資料
    makedirs(f'./.data/workspace/{user_id}/{thread_id}', exist_ok=True)
    state = State(messages=[])
    config = {
        'configurable': {
            'user_id': user_id,
            'thread_id': thread_id, 
            'workspace': f'./.data/workspace/{user_id}/{thread_id}',
            'database': 'database.db'
        }
    }

    """
    模擬用戶是否上傳資料的情境
    """
    ##  to do 

    """
    執行
    """
    workflow.invoke(state, config=config)
    while True:
        user_input = """
            我上傳了一張表"process_tracking"，
            我要對欄位"Equipment"以及欄位包含"CP_"的資料做 anova 分析，
            並將差異最大的三組找出來，把這三組的 box chart 畫出來。
        """
        if user_input == "EXIT":
            break
        result = workflow.invoke(Command(resume=user_input), config=config)
        continue
