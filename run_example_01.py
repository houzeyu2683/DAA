"""
用 LangGraph 的 create_agent 串接 mcp-server/data.py 提供的工具,
測試 LLM 能不能自己判斷該呼叫哪個 tool、填什麼參數,來回答關於資料表的問題。

執行前:
1. 先在另一個終端機把 MCP server 跑起來:
     conda run -n DAA python mcp-server/data.py
2. 再執行這支腳本:
     conda run -n DAA python run_example.py
"""

import asyncio
import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI

load_dotenv()

MODEL_URL = os.environ["MODEL_URL"]
API_KEY = os.environ["API_KEY"]
MODEL_NAME = os.environ["MODEL_NAME"]
DATA_SERVER_URL = os.environ["DATA_SERVER_URL"]

DATABASE_PATH = ".data/archive/database.db"


async def main() -> None:
    client = MultiServerMCPClient(
        {
            "data": {
                "transport": "streamable_http",
                "url": f"{DATA_SERVER_URL}/mcp",
            }
        }
    )
    tools = await client.get_tools()

    model = ChatOpenAI(model=MODEL_NAME, base_url=MODEL_URL, api_key=API_KEY)

    agent = create_agent(model, tools)

    question = f"資料庫在 {DATABASE_PATH},幫我查一下 raw_data 這張表有哪些欄位。"
    result = await agent.ainvoke({"messages": [{"role": "user", "content": question}]})

    for message in result["messages"]:
        message.pretty_print()


if __name__ == "__main__":
    asyncio.run(main())
