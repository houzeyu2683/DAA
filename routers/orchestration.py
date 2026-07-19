from nodes.orchestration import OrchestrationState

def orchestration_router(state: OrchestrationState) -> str:
    # print(state["next"])
    return state["next"]