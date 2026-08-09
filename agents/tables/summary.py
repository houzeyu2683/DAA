import base64
import mimetypes
from string import Template

import duckdb
from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain.agents import create_agent
from langchain.agents.middleware import ToolErrorMiddleware

from agents.state import State
from agents.engine import get_model


def parse_characters(characters: str) -> str:
    """避免雙重引號的參數當作輸入"""

    return characters.strip('"').strip("'")


def read_table_content(
    database_path: str,
    table_name: str,
    base_index: int = 0,
    offset_number: int = 20,
) -> dict:
    """讀取指定資料表的實際內容(數值),為了避免過長,預設指定一個索引範圍。"""

    database_path = parse_characters(database_path)
    table_name = parse_characters(table_name)

    with duckdb.connect(database_path, read_only=True) as connection:
        result = connection.execute(f"SELECT * FROM {table_name}")
        columns = [description[0] for description in result.description]
        all_rows = result.fetchall()

    row_total = len(all_rows)
    offset_index = base_index + offset_number
    rows = all_rows[base_index:offset_index]

    return {
        "columns": columns,
        "rows": rows,
        "row_total": row_total,
        "base_index": base_index,
        "offset_number": offset_number,
    }


def view_image(image_path: str) -> list:
    """讀取圖片檔案,以多模態內容格式回傳,讓有視覺能力的模型可以直接看到圖片內容並進行解讀。"""

    image_path = parse_characters(image_path)
    mime_type, _ = mimetypes.guess_type(image_path)
    with open(image_path, "rb") as image_file:
        image_code = base64.b64encode(image_file.read()).decode("utf-8")

    url = f"data:{mime_type or 'image/png'};base64,{image_code}"
    return [
        {
            "type": "image_url",
            "image_url": {"url": url},
        }
    ]


SYSTEM_CHINESE_PROMPT = Template(
    "你是一個資料分析助理系統裡負責「整合摘要報告」的執行者。\n"
    "\n"
    "# 你的職責邊界\n"
    "回顧整個對話裡到目前為止做過的事——查過哪些資料表、跑過哪些統計分析、\n"
    "產生了哪些統計結果表、畫過哪些圖表,整合寫成一份總結報告給使用者看。\n"
    "\n"
    "# 目前的上下文\n"
    "工作目錄:$session_workspace\n"
    "資料庫位置:$database_path\n"
    "資料表名稱:\n"
    "$table_names\n"
    "\n"
    "# 這次要執行的任務\n"
    "$action\n"
    "\n"
    "# 執行原則\n"
    "\n"
    "1. 用 read_table_content 讀出前面 analysis 任務產生的結果表裡實際的數值,不要只看表名就交差。\n"
    "2. 用 view_image 看懂前面 chart 任務畫的圖表內容,不要只回報圖片路徑。\n"
    "3. 把統計數值翻譯成白話的關聯性描述——說明方向(正相關/負相關)、強度(強/中/弱)、\n"
    "   代表什麼樣的關係(例如「相關係數 0.85,代表兩者關聯性很強、同增同減的趨勢很明顯」)。\n"
    "   這只是把數字翻成白話,不是在評斷這個結果「好不好」——你不做任何價值判斷。\n"
    "4. 不要重新計算或執行任何統計分析,所有數值都是前面 analysis 已經算好的,\n"
    "   你只負責讀出來、解讀、寫成報告。\n"
    "\n"
    "# 報告格式\n"
    "\n"
    "報告要包含兩個部分:\n"
    "1. 摘要:用一小段話,總結這次對話整體做了什麼、得出什麼結論。\n"
    "2. 逐項細節:條列每一個做過的任務(查了什麼、分析了什麼、畫了什麼圖),各自的結果跟白話解讀。\n"
)


def on_tool_error(exception: Exception, request) -> str:
    tool_name = request.tool_call["name"]
    tool_args = request.tool_call["args"]
    return f"{tool_name}({tool_args}) 失敗: {type(exception).__name__}: {exception}"


summary_agent = create_agent(
    get_model(),
    tools=[read_table_content, view_image],
    middleware=[ToolErrorMiddleware(on_tool_error)],
)


def summary(state: State, config: RunnableConfig) -> dict:

    session_workspace = config["configurable"]["session_workspace"]
    database_path = config["configurable"]["database_path"]
    table_names = "\n".join(
        f"- {name}" for name in config["configurable"]["table_names"]
    )
    current_task = state["tasks"][state["index"]]

    system_prompt = SYSTEM_CHINESE_PROMPT.substitute(
        session_workspace=session_workspace,
        database_path=database_path,
        table_names=table_names,
        action=current_task["action"],
    )

    try:
        result = summary_agent.invoke(
            {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    *state["messages"],
                ],
            },
        )
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

    error = any(
        isinstance(message, ToolMessage) and message.status == "error"
        for message in result["messages"]
    )

    return {"messages": result["messages"][-1:], "error": error}
