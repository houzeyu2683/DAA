import duckdb
import pandas as pd
import os
from langchain_openai import ChatOpenAI
from langgraph.graph import add_messages
from dotenv import load_dotenv
from os import getenv, makedirs
from uuid import uuid4
from langchain_core.messages import (
    SystemMessage, 
    AIMessage, 
    HumanMessage, 
    ToolMessage
)
from typing import TypedDict, Annotated
from operator import add

class Task(TypedDict):
    type: str
    description: str

class Table(TypedDict):
    name: str
    description: str

class State(TypedDict):
    messages: Annotated[list, add_messages]
    tables: Annotated[list[Table], add]
    intent: str
    tasks: list[Task]

