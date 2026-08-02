import os
from collections.abc import AsyncIterator
from typing import Any

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

from agenticend.tools.system import is_file_exist


load_dotenv()

model = ChatOpenAI(
    model=os.environ["MODEL_NAME"],
    base_url=os.environ["MODEL_URL"],
    api_key=os.environ["MODEL_KEY"],
    temperature=0,
)

# is_file_exist 先當測試工具，驗證加了 tool 之後 stream() 還能不能正常運作。
agent = create_agent(
    model,
    tools=[is_file_exist],
    checkpointer=InMemorySaver(),
)


async def stream(
    thread_id: str, user_message: str, callbacks: list[Any] | None = None
) -> AsyncIterator[str]:
    config = {"configurable": {"thread_id": thread_id}}
    if callbacks:
        config["callbacks"] = callbacks

    async for chunk, _ in agent.astream(
        {"messages": [{"role": "user", "content": user_message}]},
        config=config,
        stream_mode="messages",
    ):
        if chunk.content:
            yield chunk.content
