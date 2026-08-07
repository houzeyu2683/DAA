from typing import TypedDict

from langchain_core.runnables import RunnableConfig

from .state import State, Task
from utilities import get_model
from prompts.planning import SYSTEM_PROMPT_ZH


class Response(TypedDict):
    tasks: list[Task]


planning_agent = (
    get_model()
    .with_structured_output(Response)
    .with_retry(stop_after_attempt=3)
)


def planning(state: State, config: RunnableConfig) -> dict:

    database_path = config["configurable"]["database_path"]
    table_names = config["configurable"]["table_names"]
    table_names_text = "\n".join(f"- {name}" for name in table_names)

    system_prompt = SYSTEM_PROMPT_ZH.substitute(
        database_path=database_path,
        table_names=table_names_text,
    )

    result = planning_agent.invoke([
        {"role": "system", "content": system_prompt},
        *state["messages"],
    ])
    print(result['tasks'])
    return {"tasks": result["tasks"], "index": 0}
