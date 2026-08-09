from string import Template

import duckdb
import matplotlib
matplotlib.use("Agg")
import seaborn
from matplotlib.figure import Figure
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain.agents import create_agent
from langchain.agents.middleware import ToolErrorMiddleware

from agents.state import State
from agents.engine import get_model


def parse_characters(characters: str) -> str:
    """避免雙重引號的參數當作輸入"""

    return characters.strip('"').strip("'")


def draw_bar_chart(
    database_path: str,
    table_name: str,
    category_column: str,
    value_column: str,
    order_column: str,
    descending: bool,
    image_path: str,
    horizontal_mode: bool,
) -> dict:
    """從指定資料表讀取一個類別欄位跟一個數值欄位,依照 order_column
    (可以是欄位名稱,也可以是運算式,例如 "ABS(similarity_score)")
    排序後畫成長條圖並存檔,horizontal_mode 決定長條方向
    (True 為水平、False 為垂直)。
    常見情境是讀取 analysis 已經整理好類別與數值的結果表(例如相似度分析
    產生的結果),但不限於此,任何有類別欄位跟數值欄位的資料表都適用。"""

    database_path = parse_characters(database_path)
    table_name = parse_characters(table_name)
    category_column = parse_characters(category_column)
    value_column = parse_characters(value_column)
    order_column = parse_characters(order_column)
    image_path = parse_characters(image_path)
    direction = "DESC" if descending else "ASC"

    with duckdb.connect(database_path, read_only=True) as connection:
        data = connection.execute(
            f"SELECT {category_column}, {value_column} "
            f"FROM {table_name} "
            f"ORDER BY {order_column} {direction}"
        ).fetchdf()

    if horizontal_mode:
        # barh 會把資料的第一列畫在最下面,要反過來,
        # 畫面上由上到下才會符合 order_column/descending 指定的排序
        data = data.iloc[::-1]

    with seaborn.axes_style("whitegrid"):
        fig = Figure()
        axes = fig.subplots()
        if horizontal_mode:
            axes.barh(data[category_column], data[value_column])
            axes.set_xlabel(value_column)
            axes.set_ylabel(category_column)
        else:
            axes.bar(data[category_column], data[value_column])
            axes.set_xlabel(category_column)
            axes.set_ylabel(value_column)
        fig.savefig(image_path, bbox_inches="tight")

    return {"image_path": image_path}


SYSTEM_CHINESE_PROMPT = Template(
    "你是一個資料分析助理系統裡負責「畫圖」的執行者。\n"
    "\n"
    "# 你的職責邊界\n"
    "只負責把指定資料表的指定欄位畫成圖表並存檔。可能讀取原始資料表,也可能讀取 analysis 產生的統計結果表——\n"
    "兩者用同樣的方式處理,不需要區分。畫完圖後只回報圖片存放的位置,不需要解讀圖表內容或代表的意義,\n"
    "那是 summary 的職責,不是你的。\n"
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
    "1. 執行前如果不確定資料表或欄位的實際名稱,不要憑空假設,先確認清楚再執行。\n"
    "2. 圖片檔名要能反映這次畫的是什麼(例如用到哪些欄位),讓後續的人一看檔名就知道裡面畫了什麼。\n"
    "3. 完成後,用簡短的一句話回報就好,例如「圖表已畫完,存在 xxx」,不要長篇說明或解讀圖表內容。\n"
)


def on_tool_error(exception: Exception, request) -> str:
    tool_name = request.tool_call["name"]
    tool_args = request.tool_call["args"]
    return f"{tool_name}({tool_args}) 失敗: {type(exception).__name__}: {exception}"


chart_agent = create_agent(
    get_model(),
    tools=[draw_bar_chart],
    middleware=[ToolErrorMiddleware(on_tool_error)],
)


def chart(state: State, config: RunnableConfig) -> dict:

    session_workspace = config["configurable"]["session_workspace"]
    database_path = config["configurable"]["database_path"]
    table_names = config["configurable"]["table_names"]
    table_names_text = "\n".join(f"- {name}" for name in table_names)
    current_task = state["tasks"][state["index"]]

    system_prompt = SYSTEM_CHINESE_PROMPT.substitute(
        session_workspace=session_workspace,
        database_path=database_path,
        table_names=table_names_text,
        action=current_task["action"],
    )

    try:
        previous_messages = [
            message for message in state["messages"]
            if isinstance(message, AIMessage)
        ]
        result = chart_agent.invoke(
            {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    *previous_messages,
                ]
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
    messages = result["messages"][-1:]
    update = {"messages": messages, "error": error}
    return update
