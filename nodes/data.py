import os
from nodes.orchestration import OrchestrationState
import pandas as pd
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
import duckdb as db
from pathlib import Path
from MCP_server.client import fetch_tools
import asyncio

load_dotenv()


model_name = os.environ["MODEL_NAME"]
model_url = os.environ["MODEL_URL"]
model_key = os.environ["MODEL_KEY"]
model = ChatOpenAI(
    model=model_name,
    temperature=0,
    base_url=model_url,
    api_key=model_key,
)


server_name = os.environ["MCP_DATA_SERVER_NAME"]
server_url = os.environ["MCP_DATA_SERVER_URL"]
server_port = os.environ["MCP_DATA_SERVER_PORT"]
port = int(server_port)
tools = asyncio.run(fetch_tools(server_name, server_url, port))


# @tool
# def check_database_exist(database_path: str) -> bool:
#     """檢查資料庫是否存在"""
#     return os.path.isfile(database_path)


# @tool
# def check_table_exist(database_path: str, table_name: str) -> bool:
#     """檢查資料表是否存在"""
#     con = db.connect(database_path, read_only=True)
#     try:
#         count = con.execute(
#             "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
#             [table_name]
#         ).fetchone()[0]
#     finally:
#         con.close()
#     return count > 0


# @tool
# def get_table_shape(database_path: str, table_name: str) -> list:
#     """獲得資料表的資料數與欄位數，回傳 [row_count, col_count]。

#     參數:
#         database_path: DuckDB 資料庫檔案的路徑。
#         table_name: 要查詢的資料表名稱。
#     """
#     con = db.connect(database_path, read_only=True)
#     try:
#         row_count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
#         col_count = len(con.execute(f"DESCRIBE {table_name}").fetchall())
#     finally:
#         con.close()
#     return [row_count, col_count]


# @tool
# def load_table_to_database(table_path: str, database_path: str, table_name: str) -> dict:
    # """讀取一份資料表檔案，通常是 CSV 格式，寫入指定的 DuckDB 資料庫，成為一張新的表。

    # 參數:
    #     table_path: 檔案的路徑，通常是 CSV 格式。
    #     database_path: 要寫入的 DuckDB 資料庫檔案路徑。
    #     table_name: 寫入後的資料表名稱。
    # """
    # print("load_table_to_database")
    # # table_content = pd.read_csv(table_path)
    # # row_count, column_count = table_content.shape
    # # _create_database(database_path)
    # # _create_table(database_path, table_name, table_content)
    # Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    # con = db.connect(database_path)
    # con.execute(
    #     f"CREATE TABLE {table_name} AS SELECT * FROM read_csv_auto(?)",
    #     [table_path],
    # )

    # return {"database_path": database_path, "table_name": table_name}


# tools = [
#     load_table_to_database,
#     check_database_exist,
#     check_table_exist,
#     get_table_shape,
# ]




DATA_SYSTEM_PROMPT = (
    "你是資料載入專家，負責處理用戶的資料，用於後續分析過程，"
    "你的職責是將用戶的數據寫入資料庫中的資料表，"
    "避免後續分析時，修改用戶的原始檔案，"
    "\n\n"
    "工作區路徑(workspace)：{workspace}\n"
    "本次任務中所有資料庫、統計結果表、圖表輸出，都必須放在這個工作區底下，"
    "除非用戶另有明確指示不同路徑。"
    "\n\n"
    "禁止產生任何程式碼，"
    "回報任務的時候:"
    "- 簡短描述做了什麼"
    "- **必須明確告知資料庫位置以及資料表名稱**"
    "- **禁止**生成任何程式碼"
    "- 不要廢話"
    
)
from tools.system_tools import open_image
data_agent = create_agent(
    model,
    tools=tools + [open_image]
)


async def data_node(state: OrchestrationState, config: RunnableConfig) -> dict:
    workspace = config["configurable"]['workspace']
    data_system_prompt = DATA_SYSTEM_PROMPT.format(workspace=workspace)
    messages = [SystemMessage(content=data_system_prompt)] + state['messages']#[-1:]
    response = await data_agent.ainvoke({"messages": messages}, config={"max_concurrency": 1})

    # for message in response['messages']:
    #     message.pretty_print()

    # content = response["messages"][-1].content
    # update = {"messages": [HumanMessage(content=content)]}
    update = {"messages": response["messages"][-1:]}
    return update
