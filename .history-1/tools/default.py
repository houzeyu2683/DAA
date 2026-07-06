import json
import os
import re
import duckdb
import dotenv
from typing import Annotated
from langgraph.prebuilt import InjectedState

_ = dotenv.load_dotenv()

def get_columns(database: str, table_name: str) -> dict:
    """
    給定資料庫以及表格名稱，查詢表格的 column 名稱
    回傳有三個重要資訊
    - description:
        表格的 column 名稱描述，太多會簡化，
        讓 agent 知道的完整資訊在哪裡，必要時去自己讀取，
        不要影響上下文。
    - source:
        表格的 column 名稱完整資訊位置，
        讓 agent 後續使用可以讀取在用，
        避免直接輸入到上下文。
    - value:
        表格的 column 名稱物件，程式運行時可以直接拿來用。
    """
    con = duckdb.connect(database, read_only=True)
    rows = con.execute(f"DESCRIBE {table_name}").fetchall()
    columns = [{"name": row[0], "type": row[1]} for row in rows]
    con.close()

    os.makedirs(os.getenv("CACHE_DIR"), exist_ok=True)
    source_path = os.path.join(os.getenv("CACHE_DIR"), f"{table_name}_columns.json")
    with open(source_path, "w") as f:
        json.dump(columns, f, ensure_ascii=False, indent=2)

    names = [col["name"] for col in columns]
    if len(names) <= 12:
        description = f"Table '{table_name}' has {len(names)} columns: {', '.join(names)}. Full details at {source_path}."
    else:
        preview = ', '.join(names[:6]+names[-6:])
        description = f"Table '{table_name}' has {len(names)} columns: {preview}, ... Full details at {source_path}."

    return {
        "columns_description": description,
        "columns_source": source_path,
        "columns_value": columns,
    }

def filter_columns(
    pattern: str,
    state: Annotated[dict, InjectedState],
) -> dict:
    """
    對 get_columns 的結果做 regex 批配，篩選出符合的欄位。
    pattern 由 LLM 提供，columns_source 從 state 自動注入。
    """
    columns = json.load(open(state["columns_source"]))
    matched = [col for col in columns if re.search(pattern, col["name"])]

    os.makedirs(os.getenv("CACHE_DIR"), exist_ok=True)
    source_path = os.path.join(os.getenv("CACHE_DIR"), f"filtered_columns.json")
    with open(source_path, "w") as f:
        json.dump(matched, f, ensure_ascii=False, indent=2)

    names = [col["name"] for col in matched]
    if len(names) <= 12:
        description = f"Pattern '{pattern}' matched {len(names)} columns: {', '.join(names)}. Full details at {source_path}."
    else:
        preview = ', '.join(names[:6] + names[-6:])
        description = f"Pattern '{pattern}' matched {len(names)} columns: {preview}, ... Full details at {source_path}."

    return {
        "columns_description": description,
        "columns_source": source_path,
        "columns_value": matched,
    }


from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
import os
import dotenv

_ = dotenv.load_dotenv()

llm = ChatOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv('OPEN_ROUTER_API_KEY'),
    model="openai/gpt-oss-120b"
)
llm_with_tools = llm.bind_tools([get_columns])
messages = [
    SystemMessage("資料庫在/home/houzeyu2683/Documents/Projects/DAA/.data/workspace.db，裡面有一張my_table表"),
    HumanMessage("裡面有哪些欄位？")
]

result = llm_with_tools.invoke(messages)
print(result)


print(result.tool_calls)



messages.append(result)

for tool_call in result.tool_calls:
    tool_result = get_columns(**tool_call["args"])
    messages.append(ToolMessage(content=str(tool_result), tool_call_id=tool_call["id"]))

final = llm_with_tools.invoke(messages)


