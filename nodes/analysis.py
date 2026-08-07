from langchain_core.runnables import RunnableConfig
from langchain.agents import create_agent

from .state import State
from utilities import get_model
from prompts.analysis import SYSTEM_PROMPT_ZH
from tools.analysis import calculate_similarity


analysis_agent = create_agent(
    get_model(),
    tools=[calculate_similarity],
)


def analysis(state: State, config: RunnableConfig) -> dict:
    database_path = config["configurable"]["database_path"]
    current_task = state["tasks"][state["index"]]

    system_prompt = SYSTEM_PROMPT_ZH.substitute(
        database_path=database_path,
        action=current_task["action"],
    )

    result = analysis_agent.invoke({
        "messages": [{"role": "system", "content": system_prompt}],
    })

    return {"messages": result["messages"]}
