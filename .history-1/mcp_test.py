import asyncio
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
import os
import dotenv

_ = dotenv.load_dotenv()

async def main():
    client = MultiServerMCPClient(
        {
            "daa": {
                "url": "http://localhost:8000/sse",
                "transport": "sse",
            }
        }
    )
    tools = await client.get_tools()
    print("Available tools:", [t.name for t in tools])

    llm = ChatOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv('OPEN_ROUTER_API_KEY'),
        model="openai/gpt-oss-120b"
    )
    llm_with_tools = llm.bind_tools(tools)

    response = await llm_with_tools.ainvoke("Please add 3 and 5.")
    print("Response:", response)


if __name__ == "__main__":
    asyncio.run(main())
