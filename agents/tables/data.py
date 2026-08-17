import os
import re
from string import Template

import duckdb
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain.agents import create_agent

from agents.middleware import ToolErrorMiddleware
from agents.state import State
from agents.engine import get_model


def parse_characters(characters: str) -> str:
    """避免雙重引號的參數當作輸入"""

    return characters.strip('"').strip("'")


def is_database_exist(database_path: str) -> bool:
    """檢查資料庫是否存在。"""

    database_path = parse_characters(database_path)
    return os.path.isfile(database_path)


def is_table_exist(database_path: str, table_name: str) -> bool:
    """檢查某個資料表是否存在。"""

    database_path = parse_characters(database_path)
    table_name = parse_characters(table_name)

    with duckdb.connect(database_path, read_only=True) as connection:
        all_tables = connection.execute("SHOW TABLES").fetchall()

    return table_name in [name for (name,) in all_tables]


def list_table_overview(database_path: str) -> dict:
    """列出所有的資料表，暫時不考慮上百個資料表情況，如果未來需要再補分頁功能。"""

    database_path = parse_characters(database_path)

    with duckdb.connect(database_path, read_only=True) as connection:

        all_tables = connection.execute("SHOW TABLES").fetchall()
        loop_items = []
        for (table_name,) in all_tables:
            row_number = connection.execute(
                f"SELECT COUNT(*) FROM {table_name}"
            ).fetchone()[0]
            column_number = len(
                connection.execute(f"DESCRIBE {table_name}").fetchall()
            )
            table = {
                "table_name": table_name,
                "row_number": row_number,
                "column_number": column_number,
            }
            loop_items.append(table)
            continue

        table_profiles = loop_items

    table_total = len(table_profiles)
    return {"table_total": table_total, "table_profiles": table_profiles}


def search_columns(
    database_path: str,
    table_name: str,
    regular_expression: str,
    row_index: int = 0,
    row_offset: int = 10,
) -> dict:
    """用正規表達式搜尋指定資料表裡符合的欄位名稱與型態,為了避免過長,預設指定一個索引範圍。"""

    database_path = parse_characters(database_path)
    table_name = parse_characters(table_name)

    with duckdb.connect(database_path, read_only=True) as connection:
        all_columns = connection.execute(
            f"DESCRIBE {table_name}"
        ).fetchall()

    pattern = re.compile(regular_expression)
    matched_columns = [
        (name, column_type) for name, column_type, *_ in all_columns
        if pattern.search(name)
    ]
    search_column_total = len(matched_columns)
    if search_column_total <= row_offset:
        page = matched_columns
        search_column_names = [name for name, _ in page]
        search_column_type = [column_type for _, column_type in page]
        notice_message = "可以顯示全部" 
        return {
            "search_column_total": search_column_total,
            "search_column_names": search_column_names,
            "search_column_type": search_column_type,
            "row_index": row_index,
            "row_offset": row_offset,
            "notice_message": notice_message
        }

    page = matched_columns[row_index: row_index + row_offset]
    search_column_names = [name for name, _ in page]
    search_column_type = [column_type for _, column_type in page]
    notice_message = "過多以至於無法顯示全部" 
    return {
        "search_column_total": search_column_total,
        "search_column_names": search_column_names,
        "search_column_type": search_column_type,
        "row_index": row_index,
        "row_offset": row_offset,
        "notice_message": notice_message
    }


def list_distinct_values(database_path: str, table_name: str, column_name: str) -> dict:
    """列出指定欄位裡所有不重複的值。"""

    return


def count_null_values(database_path: str, table_name: str, column_name: str) -> dict:
    """計算指定欄位裡有多少筆資料是缺失值(NULL)。"""

    return


def count_duplicate_rows(database_path: str, table_name: str) -> dict:
    """計算指定資料表裡有多少筆完全重複的紀錄。"""

    return


SYSTEM_CHINESE_PROMPT = Template(
    "你是一個資料分析助理系統裡負責「瀏覽資料庫」的執行者。\n"
    "\n"
    "# 你的職責邊界\n"
    "只負責瀏覽資料庫的結構與基本資訊——有哪些資料表、資料表的欄位、資料筆數(shape)、資料表是否存在等,\n"
    "不做任何統計計算(例如平均值、標準差、相關性分析),那些是 analysis 的職責,不是你的。\n"
    "\n"
    "# 目前的上下文\n"
    "工作目錄:$session_workspace\n"
    "資料庫位置:$database_path\n"
    "資料表名稱:\n"
    "$table_names\n"
    "\n"
    "# 這次要執行的任務\n"
    "$current_task\n"
    "\n"
    "# 執行原則\n"
    "\n"
    "1. 資料庫可能有很多資料表、很多欄位,呼叫工具時善用分頁參數,不要一次要求過多筆數,避免塞爆你自己的 context。\n"
    "2. 執行前如果不確定資料庫檔案還在不在,可以先用檢查檔案/資料夾是否存在的工具確認,不要直接假設一定存在。\n"
    "3. 完成後,用清楚的一段話總結你查到的結果(有哪些表、哪些欄位、資料型態、筆數等),讓後續的人不需要重新查一次\n"
    "   就能理解資料庫的樣貌。\n"
)


def on_tool_error(exception: Exception, request) -> str:
    tool_name = request.tool_call["name"]
    tool_args = request.tool_call["args"]
    return f"{tool_name}({tool_args}) 失敗: {type(exception).__name__}: {exception}"


data_agent = create_agent(
    get_model(),
    tools=[is_database_exist, is_table_exist, list_table_overview, search_columns],
    middleware=[ToolErrorMiddleware(on_tool_error)],
)


async def data(state: State, config: RunnableConfig) -> dict:

    session_workspace = config["configurable"]["session_workspace"]
    database_path = config["configurable"]["database_path"]
    table_names = "\n".join(
        f"- {name}" for name in config["configurable"]["table_names"]
    )
    current_task = state["tasks"][state["index"]]["action"]

    system_prompt = SYSTEM_CHINESE_PROMPT.substitute(
        session_workspace=session_workspace,
        database_path=database_path,
        table_names=table_names,
        current_task=current_task,
    )

    try:
        previous_messages = [
            message for message in state["messages"]
            if isinstance(message, AIMessage)
        ]
        prompt_request = {
            "messages": [
                {"role": "system", "content": system_prompt},
                *previous_messages,
            ]
        }
        prompt_response = await data_agent.ainvoke(prompt_request, config=config)
    except Exception as exception:
        update = {
            "messages": [
                {
                    "role": "assistant",
                    "content": (
                        f"失敗: {type(exception).__name__}: {exception}"
                    ),
                }
            ],
            "error": True
        }
        return update

    messages = prompt_response["messages"][-1:]
    error = any(
        isinstance(message, ToolMessage) and message.status == "error"
        for message in prompt_response["messages"]
    )
    update = {"messages": messages, "error": error}
    return update
