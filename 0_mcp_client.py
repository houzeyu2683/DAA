"""
Notebook 0(client 端):用最原始的 MCP client 連上 0_mcp_server.py,
確認 list_tools / call_tool 這兩個核心動作能正常運作。
不經過 LangGraph、不經過 LLM,單純驗證 MCP 協議這一層本身沒問題。

先在另一個終端機把 server 跑起來:
    conda run -n DAA python notebooks\0_mcp_server.py
再執行這支腳本。
"""

import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

SERVER_URL = "http://127.0.0.1:8000/mcp"


async def main() -> None:
    async with streamable_http_client(SERVER_URL) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("=== 可用工具 ===")
            for tool in tools.tools:
                print(f"- {tool.name}: {tool.description}")
                print(f"  input_schema: {tool.inputSchema}")

            print("\n=== 呼叫 echo ===")
            result = await session.call_tool("echo", {"text": "hello mcp"})
            print(result.content)

            print("\n=== 呼叫 add ===")
            result = await session.call_tool("add", {"a": 1, "b": 2})
            print(result.content)

            print("\n=== 呼叫 sum_list ===")
            result = await session.call_tool("sum_list", {"numbers": [1, 2, 3, 4]})
            print(result.content)

            print("\n=== 呼叫 describe_lineage ===")
            result = await session.call_tool(
                "describe_lineage",
                {"name": "monthly_summary", "parent_tables": ["orders", "customers"]},
            )
            print(result.content)

            print("\n=== 情境示範:挑 device_ 欄位算 correlation ===")

            print("\n步驟 1 - 用 run_sql 查欄位名(不寫死哪些欄位)")
            result = await session.call_tool(
                "run_sql",
                {
                    "query": "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'sensor_readings'"
                },
            )
            print(result.content)

            print("\n步驟 2 - 用 run_python 篩選 device_ 欄位 + 算 corr matrix")
            code = (
                "cols = [c for c in df.columns if 'device_' in c]\n"
                "df[cols].corr()"
            )
            result = await session.call_tool("run_python", {"code": code})
            print(result.content)


if __name__ == "__main__":
    asyncio.run(main())

# === 可用工具 ===
# - echo: 把傳入的文字原封不動送回去,用來確認串接有沒有通。
#   input_schema: {'properties': {'text': {'title': 'Text', 'type': 'string'}}, 'required': ['text'], 'title': 'echoArguments', 'type': 'object'}
# - add: 回傳 a + b。
#   input_schema: {'properties': {'a': {'title': 'A', 'type': 'integer'}, 'b': {'title': 'B', 'type': 'integer'}}, 'required': ['a', 'b'], 'title': 'addArguments', 'type': 'object'}

# === 呼叫 echo ===
# [TextContent(type='text', text='hello mcp', annotations=None, meta=None)]

# === 呼叫 add ===
# [TextContent(type='text', text='3', annotations=None, meta=None)]