from nodes.orchestration import OrchestrationState

def orchestration_router(state: OrchestrationState) -> str:
    return state["next"]