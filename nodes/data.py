import os
from nodes.coordination import CoordinationState
import pandas as pd
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from tools.default import (
    check_file_exist,
    check_database_exist,
    create_database,
    check_table_exist,
    create_table,
    list_tables,
)


load_dotenv()
MODEL_NAME = os.environ["MODEL_NAME"]
MODEL_URL = os.environ["MODEL_URL"]
API_KEY = os.environ["API_KEY"]
model = ChatOpenAI(
    model=MODEL_NAME,
    temperature=0,
    base_url=MODEL_URL,
    api_key=API_KEY,
)


@tool
def load_table_to_database(table_path: str, database_path: str, table_name: str) -> dict:
    """讀取一份資料表檔案，通常是 CSV 格式，寫入指定的 DuckDB 資料庫，成為一張新的表。

    參數:
        table_path: 檔案的路徑，通常是 CSV 格式。
        database_path: 要寫入的 DuckDB 資料庫檔案路徑。
        table_name: 寫入後的資料表名稱。
    """
    table_content = pd.read_csv(table_path)
    row_count, _ = table_content.shape
    created_table = create_table.invoke({
        "database_path": database_path,
        "table_name": table_name,
        "table_content": table_content,
    })

    return {"table_name": table_name, "row_count": row_count, "created_table": created_table}


tools = [
    check_file_exist,
    check_database_exist,
    check_table_exist,
    create_database,
    load_table_to_database,
    list_tables,
]


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

data_agent = create_agent(
    model,
    tools=tools,
    # system_prompt=DATA_SYSTEM_PROMPT,
)


def data_node(state: CoordinationState, config: RunnableConfig) -> dict:
    content = DATA_SYSTEM_PROMPT.format(workspace=config["configurable"]['workspace'])
    messages = [SystemMessage(content=content)] + state['messages']#[-1:]
    response = data_agent.invoke({"messages": messages})

    for message in response['messages']:
        message.pretty_print()

    update = {"messages": response["messages"][1:]}
    return update
