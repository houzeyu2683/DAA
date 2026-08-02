from collections.abc import AsyncIterator
from typing import Any

from agenticend.utilities import get_agent


async def stream(
    thread_id: str, user_message: str, callbacks: list[Any] | None = None
) -> AsyncIterator[str]:
    agent = get_agent()
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

