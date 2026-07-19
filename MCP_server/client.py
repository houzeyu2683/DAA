import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient


async def fetch_tools(server_name: str, server_host: str, server_port: int) -> list:
    client = MultiServerMCPClient({
        server_name: {
            "transport": "streamable_http",
            "url": f"http://{server_host}:{server_port}/mcp",
        },
    })
    return await client.get_tools()