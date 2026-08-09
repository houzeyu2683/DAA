import re
from string import Template

import duckdb
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain.agents import create_agent
from langchain.agents.middleware import ToolErrorMiddleware

from agents.state import State
from agents.engine import get_model


NUMERIC_COLUMN_TYPES = {
    "TINYINT", "SMALLINT", "INTEGER", "BIGINT", "HUGEINT",
    "UTINYINT", "USMALLINT", "UINTEGER", "UBIGINT",
    "DECIMAL", "DOUBLE", "FLOAT", "REAL",
}


def parse_characters(characters: str) -> str:
    """避免雙重引號的參數當作輸入"""

    return characters.strip('"').strip("'")


def calculate_similarity(
    database_path: str,
    source_name: str,
    left_column: str,
    right_columns: str,
    result_name: str,
) -> dict:
    """計算指定資料表中,以 left_column 這個基準欄位,跟符合 right_columns
    正規表達式的所有數值欄位,逐一計算皮爾森相關係數(一對多比對),
    結果存成新的資料表寫回資料庫,只回傳這張表的名稱與配對總數。
    left_column 是這次分析的基準,必須是資料表裡實際存在的精確欄位名稱,
    不是正規表達式,一次只能指定一個欄位;right_columns 則是拿來跟基準
    逐一比對的一群欄位,用正規表達式指定,可以同時符合多個。
    如果 left_column 不存在、或不是數值型態,會回傳錯誤說明,不會中斷執行。
    right_columns 比對到的欄位如果不是數值型態,會自動略過,不會拿去計算。
    right_columns 這個正規表達式是用子字串比對(只要 pattern 出現在欄位名稱
    的任何位置就算符合),如果只想比對到名稱完全等於某個欄位,
    請用 ^欄位名$ 這種寫法明確指定完整比對,否則可能會意外比對
    到名稱裡剛好包含這段文字的其他欄位。"""

    database_path = parse_characters(database_path)
    source_name = parse_characters(source_name)
    left_column = parse_characters(left_column)
    right_columns = parse_characters(right_columns)
    result_name = parse_characters(result_name)

    right_pattern = re.compile(right_columns)

    with duckdb.connect(database_path) as connection:
        all_columns = connection.execute(
            f"DESCRIBE {source_name}"
        ).fetchall()

        column_types = {
            name: column_type for name, column_type, *_ in all_columns
        }

        if left_column not in column_types:
            notice_message = (
                f"left_column 必須是資料表裡實際存在的精確欄位名稱,"
                f"但找不到叫做 '{left_column}' 的欄位。"
            )
            return {"notice_message": notice_message}

        if column_types[left_column].upper() not in NUMERIC_COLUMN_TYPES:
            notice_message = (
                f"left_column '{left_column}' 存在,但不是數值型態,"
                "無法計算相關係數。"
            )
            return {"notice_message": notice_message}

        matched_right_columns = [
            name for name, column_type, *_ in all_columns
            if (
                right_pattern.search(name)
                and column_type.upper() in NUMERIC_COLUMN_TYPES
            )
        ]

        if not matched_right_columns:
            notice_message = (
                "沒有比對到任何符合條件的數值欄位,"
                "請確認正規表達式,或欄位是否為數值型態。"
            )
            return {
                "notice_message": notice_message,
                "right_columns": matched_right_columns,
            }

        pair_queries = [
            f"SELECT '{left_column}' AS basis_target, "
            f"'{right}' AS compare_variables, "
            f"corr({left_column}, {right}) AS similarity_score "
            f"FROM {source_name}"
            for right in matched_right_columns
        ]
        select_query = " UNION ALL ".join(pair_queries)
        connection.execute(
            f"CREATE OR REPLACE TABLE {result_name} AS {select_query}"
        )
        #   basis_target       compare_variables  similarity_score
        # 0         age         key_passes   -0.061195
        # 1         age  successful_passes   -0.047853
        # 2         age       total_passes   -0.046014
    pair_total = len(matched_right_columns)
    return {
        "result_name": result_name,
        "pair_total": pair_total,
        "result_columns": {
            "basis_target": "基準的欄位名稱,這次分析固定拿來當比較基準的欄位",
            "compare_variables": "被比對的欄位名稱,逐一跟基準欄位比較的分析目標",
            "similarity_score": (
                "皮爾森相關係數,範圍 -1 到 1,不分正負,"
                "絕對值越大代表相關性越強"
            ),
        },
    }


def get_top_rows(
    database_path: str,
    table_name: str,
    order_column: str,
    descending: bool,
    limit: int,
) -> dict:
    """依照指定的欄位或運算式(例如 "similarity" 或 "ABS(similarity)"),
    對指定資料表排序,只回傳前 limit 筆資料,用來快速找出某個指標
    最大/最小的前幾筆,不用把整張表的內容都讀出來。
    如果 order_column 有誤(例如欄位不存在、運算式語法錯誤),
    會回傳錯誤說明,不會中斷執行。"""

    database_path = parse_characters(database_path)
    table_name = parse_characters(table_name)
    order_column = parse_characters(order_column)
    direction = "DESC" if descending else "ASC"

    with duckdb.connect(database_path, read_only=True) as connection:
        rows = connection.execute(
            f"SELECT * FROM {table_name} "
            f"ORDER BY {order_column} {direction} "
            f"LIMIT {limit}"
        ).fetchall()
        columns = [
            description[0] for description in connection.description
        ]

    return {
        "columns": columns,
        "rows": rows,
        "row_total": len(rows),
    }


SYSTEM_CHINESE_PROMPT = Template(
    "你是一個資料分析助理系統裡負責「統計分析」的執行者。\n"
    "\n"
    "# 你的職責邊界\n"
    "只負責對指定資料表的指定欄位做統計分析。分析結果不會直接告訴使用者,而是存成一張新的資料表寫回資料庫,\n"
    "你只需要回報這張結果表的名稱。瀏覽資料庫結構、欄位這種不需要計算的事,是 data 的職責,不是你的。\n"
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
    "1. 執行統計分析前,如果不確定欄位的實際名稱或型態,不要憑空假設,先確認清楚再執行。\n"
    "2. 結果表的名稱要能反映這次分析的內容(例如用到哪些欄位、做了什麼分析),讓後續的人一看名稱就知道裡面存了什麼。\n"
    "3. 完成後,用簡短的一句話回報就好,例如「分析完成,結果存在 xxx 表」,不要長篇說明。\n"
    "   如果工具回傳的結果裡有附上結果表的欄位說明,要把這些說明一併寫進回報裡,\n"
    "   讓後續需要查詢這張表的人知道每個欄位代表什麼、該怎麼用。\n"
    "   「簡短」不代表可以省略任務要求的具體結論——如果任務問的是某個特定答案\n"
    "   (例如哪一筆最大、最小、符合某個條件),這個答案本身一定要寫進回報裡,\n"
    "   不能只說「已完成、存在哪張表」而漏掉真正要回答的內容。\n"
    "4. 不要解讀或評論統計結果本身的意義(例如不要說「這個相關係數代表兩者關係很強」這種話)——結果該怎麼\n"
    "   解讀是 summary 的職責,不是你的。你只回報「做了什麼、存在哪」,不判斷結果好不好、代表什麼。\n"
)


def on_tool_error(exception: Exception, request) -> str:
    tool_name = request.tool_call["name"]
    tool_args = request.tool_call["args"]
    return f"{tool_name}({tool_args}) 失敗: {type(exception).__name__}: {exception}"


analysis_agent = create_agent(
    get_model(),
    tools=[calculate_similarity, get_top_rows],
    middleware=[ToolErrorMiddleware(on_tool_error)],
)


def analysis(state: State, config: RunnableConfig) -> dict:

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
        prompt_response = analysis_agent.invoke(prompt_request)
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
