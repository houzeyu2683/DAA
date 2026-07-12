import asyncio
import json
from typing import Optional
import os

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_mcp_adapters.client import MultiServerMCPClient

from core.functions import get_model
from core.state import State

from dotenv import load_dotenv

_ = load_dotenv()
DATA_SERVER_URL = os.getenv("DATA_SERVER_URL")

_model = get_model()

_SYSTEM_TEMPLATE = """
你是 DATA Agent，負責把使用者的原始資料存進個人資料庫。
禁止查詢、篩選或修改資料。
user workspace: {workspace}
user database: {database}
"""

_client = MultiServerMCPClient({
    "data": {
        "transport": "sse",
        "url": f"{DATA_SERVER_URL}/sse",
    }
})

def data_processing(state: State, config: RunnableConfig) -> dict:
    # tools = _client.get_tools()
    tools = asyncio.run(_client.get_tools())
    tools_by_name = {tool.name: tool for tool in tools}
    # print([t.name for t in tools])
    model_with_tools = _model.bind_tools(tools)
    
    workspace = config['configurable']['workspace']
    database = config['configurable']['database']
    task = state['tasks'][0]
    conversation = [
        SystemMessage(_SYSTEM_TEMPLATE.format(workspace=workspace, database=database)),
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





