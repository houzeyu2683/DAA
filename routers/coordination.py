from nodes.coordination import CoordinationState

def coordination_router(state: CoordinationState) -> str:
    return state["next"]