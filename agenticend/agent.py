import os
from collections.abc import AsyncIterator

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver


load_dotenv()

model = ChatOpenAI(
    model=os.environ["MODEL_NAME"],
    base_url=os.environ["MODEL_URL"],
    api_key=os.environ["MODEL_KEY"],
    temperature=0,
)

# 還沒接工具，先用空 tools 讓 agent 純聊天，之後照規劃再慢慢補上。
agent = create_agent(
    model,
    tools=[],
    checkpointer=InMemorySaver(),
)


async def stream(thread_id: str, user_message: str) -> AsyncIterator[str]:
    config = {"configurable": {"thread_id": thread_id}}
    async for chunk, _ in agent.astream(
        {"messages": [{"role": "user", "content": user_message}]},
        config=config,
        stream_mode="messages",
    ):
        if chunk.content:
            yield chunk.content
