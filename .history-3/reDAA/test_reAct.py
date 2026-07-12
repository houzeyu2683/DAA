import asyncio
import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import InMemorySaver

from agent.middleware import CsvIngestMiddleware

_ = load_dotenv()

model = init_chat_model(
    model=os.environ["MODEL_NAME"],
    model_provider="openai",
    base_url=os.environ["MODEL_URL"],
    api_key=os.environ["API_KEY"],
    temperature=0,
)

config = {"configurable": {"thread_id": "test-1"}}

SYSTEM_PROMPT = """\
你是一個資料分析助理。所有資料都存放在 DuckDB 裡，你只能透過提供的工具
（list_tables、get_schema、compute_group_difference、plot_boxplot）查詢與分析，
不可以嘗試直接讀取 CSV 檔案內容或憑空假設資料長相。

使用者提到的 CSV 檔案會被系統自動載入 DuckDB（你會在對話中看到
「[系統自動載入]」訊息，裡面有 table 名稱與欄位），你不需要、也不應該
自己嘗試載入資料。

如果使用者的任務描述中有缺漏或模糊的地方（例如欄位名稱不存在、條件不清楚），
你必須先呼叫 get_schema 或 list_tables 確認，或向使用者提出具體問題來確認，
不可以自己假設或亂猜。
"""

MCP_URL = os.environ.get("DATA_SERVER_URL", "http://localhost:8001") + "/mcp"

GOAL_TASK = '''\
讀取"device_3000.csv"，我要針對"sensor_avg"欄位跟包含"machine"欄位進行差異分析，\
將差異最大的前五個結果，用 box-chart 呈現出來\
'''


async def main() -> None:
    mcp_client = MultiServerMCPClient(
        {"duckdb": {"transport": "streamable_http", "url": MCP_URL}}
    )
    all_tools = await mcp_client.get_tools(server_name="duckdb")
    # ingest_csv is called deterministically by CsvIngestMiddleware, not by the LLM.
    agent_tools = [t for t in all_tools if t.name != "ingest_csv"]

    agent = create_agent(
        model,
        tools=agent_tools,
        system_prompt=SYSTEM_PROMPT,
        middleware=[CsvIngestMiddleware(mcp_client)],
        checkpointer=InMemorySaver(),
    )

    user_input = GOAL_TASK
    while True:
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": user_input}]}, config
        )
        reply = result["messages"][-1].content
        print(f"\nAgent: {reply}\n")
        user_input = input("你: ")
        if user_input.strip().lower() in {"exit", "quit"}:
            break


if __name__ == "__main__":
    asyncio.run(main())
