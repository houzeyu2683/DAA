from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
import asyncio
import json
from typing import Optional
import os

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from core.state import State
import os
from core.functions import get_model
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

_ = load_dotenv()
STATS_SERVER_URL = os.getenv("STATS_SERVER_URL")

_model = get_model()

_SYSTEM_TEMPLATE = """
你是 STATS Agent，負責挑選合適的統計工具，完成指定的統計分析工作

user workspace: {workspace}
user database: {database}
user table: {table}
"""

_client = MultiServerMCPClient({
    "data": {
        "transport": "sse",
        "url": f"{STATS_SERVER_URL}/sse",
    }
})

def stats_processing(state: State, config: RunnableConfig) -> dict:
    """對資料執行統計分析（如 ANOVA），並整理出差異最大的項目。"""

    tools = asyncio.run(_client.get_tools())
    tools_by_name = {tool.name: tool for tool in tools}
    print(len(tools_by_name))
    # print([t.name for t in tools])
    model_with_tools = _model.bind_tools(tools)
    
    workspace = config['configurable']['workspace']
    database = config['configurable']['database']
    task = state['tasks'][0]
    conversation = [
        SystemMessage(_SYSTEM_TEMPLATE.format(workspace=workspace, database=database, table=table)),
        HumanMessage(task['instruction'])
    ]
    response = model_with_tools.invoke(conversation)
    for call in response.tool_calls:
        tool = tools_by_name[call["name"]]
        # result = tool.invoke(call["args"])
        result = asyncio.run(tool.ainvoke(call["args"]))
        continue
    print(result[0]['text'])
    infomation = json.loads(result[0]['text'])

    messages = [AIMessage(task['instruction']), AIMessage(infomation['description'])]
    
    # state['messages']
    # task = state['tasks'][0]
    # task['instruction']
    # response = model_with_tools.ainvoke(messages)
    for i in messages:
        print(i)
        continue
    return {
        'tables': [infomation['table_name']],
        "messages": messages,
        'tasks': state['tasks'][1:]
    }


    return {}
