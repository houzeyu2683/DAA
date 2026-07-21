import os
import uuid

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

from tools.default_tools import (
    is_file_exist,
    create_database,
    create_table,
    is_columns_exist,
    select_columns,
    preview_table,
    export_table,
)


load_dotenv()

model = ChatOpenAI(
    model=os.environ["MODEL_NAME"],
    base_url=os.environ["MODEL_URL"],
    api_key=os.environ["MODEL_KEY"],
    temperature=0,
    model_kwargs={"parallel_tool_calls": False},
)

tools = [
    is_file_exist,
    create_database,
    create_table,
    is_columns_exist,
    select_columns,
    preview_table,
    export_table,
]

agent = create_agent(model, tools=tools, checkpointer=InMemorySaver())

config = {"configurable": {"thread_id": str(uuid.uuid4())}}


if __name__ == "__main__":
    print("多輪對話測試，輸入 exit 離開。")
    prev_len = 0
    while True:
        user_input = input("\n你: ")
        if user_input.strip().lower() in {"exit", "quit"}:
            break

        response = agent.invoke(
            {"messages": [{"role": "user", "content": user_input}]},
            config=config,
        )

        for message in response["messages"][prev_len:]:
            message.pretty_print()
        prev_len = len(response["messages"])
