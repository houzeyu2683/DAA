import os
import asyncio
from typing import TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langgraph.graph import StateGraph, START, END
from langchain_core.runnables import RunnableConfig

load_dotenv()

model = ChatOpenAI(
    model=os.environ["MODEL_NAME"],
    base_url=os.environ["MODEL_URL"],
    api_key=os.environ["MODEL_KEY"],
    temperature=0,
)


class State(TypedDict):
    messages: list


# node 內部才建立 create_agent，模擬你實際的寫法
async def node_a(state: State, config: RunnableConfig) -> dict:
    agent_a = create_agent(model, tools=[])
    result = await agent_a.ainvoke(
        {"messages": state["messages"]},
        config=config,  # 原封不動轉傳，不用自己組 callbacks
    )
    return {"messages": result["messages"]}


async def node_b(state: State, config: RunnableConfig) -> dict:
    agent_b = create_agent(model, tools=[])
    result = await agent_b.ainvoke(
        {"messages": state["messages"] + [{"role": "user", "content": "換個角度再講一次"}]},
        config=config,
    )
    return {"messages": result["messages"]}


graph = StateGraph(State)
graph.add_node("node_a", node_a)
graph.add_node("node_b", node_b)
graph.add_edge(START, "node_a")
graph.add_edge("node_a", "node_b")
graph.add_edge("node_b", END)
app = graph.compile()


async def main():
    inputs = {"messages": [{"role": "user", "content": "用一句話介紹台灣"}]}

    prev_node = None
    async for chunk, metadata in app.astream(inputs, stream_mode="messages"):
        node_name = metadata.get("langgraph_node", "?")
        if node_name != prev_node:
            print(f"\n[{node_name}] ", end="")
            prev_node = node_name
        print(chunk.content, end="", flush=True)
    print()


if __name__ == "__main__":
    asyncio.run(main())
