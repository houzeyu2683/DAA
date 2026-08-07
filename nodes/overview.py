from langchain_core.runnables import RunnableConfig
from langchain.agents import create_agent

from .state import State
from utilities import get_model
from prompts.overview import SYSTEM_PROMPT_ZH
from tools.overview import is_file_exist, is_folder_exist, list_table_names


overview_agent = create_agent(
    get_model(),
    tools=[is_file_exist, is_folder_exist, list_table_names],
)


def overview(state: State, config: RunnableConfig) -> dict:

    database_path = config["configurable"]["database_path"]
    current_task = state["tasks"][state["index"]]

    system_prompt = SYSTEM_PROMPT_ZH.substitute(
        database_path=database_path,
        action=current_task["action"],
    )

    result = overview_agent.invoke({
        "messages": [{"role": "system", "content": system_prompt}],
    })

    return {"messages": result["messages"][-1:]}
