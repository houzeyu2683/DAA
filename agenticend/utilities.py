import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

from agenticend.tools.system import is_file_exist


load_dotenv()

_agent = None


def get_agent():
    global _agent
    if _agent is None:
        model = ChatOpenAI(
            model=os.environ["MODEL_NAME"],
            base_url=os.environ["MODEL_URL"],
            api_key=os.environ["MODEL_KEY"],
            temperature=0,
        )
        _agent = create_agent(
            model,
            tools=[is_file_exist],
            checkpointer=InMemorySaver(),
        )
    return _agent
