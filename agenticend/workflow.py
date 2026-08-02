import os

import dotenv
from langchain import agents
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.state import CompiledStateGraph


dotenv.load_dotenv()
short_memory = InMemorySaver()


def get_agent() -> CompiledStateGraph:
    
    model = ChatOpenAI(
        model=os.environ["MODEL_NAME"],
        base_url=os.environ["MODEL_URL"],
        api_key=os.environ["MODEL_KEY"],
        temperature=0,
    )
    agent = agents.create_agent(
        model,
        tools=[],
        checkpointer=short_memory,
    )
    return agent
