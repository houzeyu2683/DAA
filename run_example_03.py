"""
用 LangGraph 的 create_agent 建立雙層 agent 架構,達到「讀資料的流程看不到統計工具、
做統計的流程看不到資料工具」的隔離:

- 主 agent:只綁定 data-server 的工具(load_table、get_schema) + 一個
  「委派給統計專家」的工具。看不到任何個別的統計方法。
- 統計子 agent:只綁定 stats-server 的工具(anova_by_pattern,未來會增加更多)。
  看不到 load_table、get_schema。主 agent 呼叫它時,只能用自然語言描述需求,
  它自己決定要用哪個統計方法、怎麼填參數。

執行前:
1. 分別在兩個終端機把兩個 MCP server 跑起來:
     conda run -n DAA python mcp-server/data.py
     conda run -n DAA python mcp-server/stats.py
2. 再執行這支腳本:
     conda run -n DAA python run_example_03.py
"""

import asyncio
import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI

load_dotenv()

MODEL_URL = os.environ["MODEL_URL"]
API_KEY = os.environ["API_KEY"]
MODEL_NAME = os.environ["MODEL_NAME"]
DATA_SERVER_URL = os.environ["DATA_SERVER_URL"]
STATS_SERVER_URL = os.environ["STATS_SERVER_URL"]

DATABASE_PATH = ".data/tmp/database.db"

# 主 agent、統計子 agent 都需要知道資料庫路徑,所以共用同一段話。
DATABASE_PROMPT = (
    "這次對話已經分配了一個專屬的工作空間,"
    f"裡面的 DuckDB 資料庫路徑是:{DATABASE_PATH}。\n"
    "凡是工具需要 database_path 這個參數時,一律使用這個路徑,"
    "不要自己猜測或編造其他路徑。"
)

MAIN_SYSTEM_PROMPT = "你是一個資料分析助理。" + DATABASE_PROMPT
STATS_SYSTEM_PROMPT = (
    "你是統計分析專家,根據使用者需求選擇合適的統計方法並執行。" + DATABASE_PROMPT
)


async def main() -> None:
    client = MultiServerMCPClient(
        {
            "data": {
                "transport": "streamable_http",
                "url": f"{DATA_SERVER_URL}/mcp",
            },
            "stats": {
                "transport": "streamable_http",
                "url": f"{STATS_SERVER_URL}/mcp",
            },
        }
    )
    data_tools = await client.get_tools(server_name="data")
    stats_tools = await client.get_tools(server_name="stats")

    model = ChatOpenAI(model=MODEL_NAME, base_url=MODEL_URL, api_key=API_KEY)

    stats_agent = create_agent(model, tools=stats_tools, system_prompt=STATS_SYSTEM_PROMPT)

    @tool
    async def run_statistical_analysis(request: str) -> str:
        """當使用者的需求涉及統計分析(例如變異數分析、相關係數、假設檢定等)時,
        呼叫這個工具。request 裡務必包含:要分析的表名(table_name)、
        想比較/分組的欄位、以及使用者想知道什麼,用自然語言描述清楚,
        交給專門的統計分析專家處理。"""
        result = await stats_agent.ainvoke({"messages": [{"role": "user", "content": request}]})
        return result["messages"][-1].content

    main_agent = create_agent(
        model,
        tools=[*data_tools, run_statistical_analysis],
        system_prompt=MAIN_SYSTEM_PROMPT,
    )

    question = (
        "幫我讀取 '.data/archive/fifa_world_cup_2026_player_performance.csv',"
        "然後幫我看看球員的 position(位置)分組之下,"
        "所有欄位名稱包含 'goals' 的數值欄位,是否有顯著差異。"
    )
    result = await main_agent.ainvoke({"messages": [{"role": "user", "content": question}]})

    for message in result["messages"]:
        message.pretty_print()


if __name__ == "__main__":
    asyncio.run(main())
