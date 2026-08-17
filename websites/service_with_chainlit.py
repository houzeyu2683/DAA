import os
import re
import sys
from pathlib import Path
from string import Template

import duckdb
import chainlit as cl

# chainlit run 只會把這個檔案所在的資料夾（websites/）加進 sys.path，
# 不會加專案根目錄，所以要自己把根目錄加進去，才能 import agents 套件。
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.workflow import Workflow, graph


# ============================================================
# 第一區：agent 串接
# ============================================================
# Workflow.stream() 已經把 LangGraph 的原始事件整理成
# {"level": "node"/"tool_call"/"tool_result", ...} 這種結構化格式,
# 這裡不需要再自己解析 message.type/tool_calls。

workflow = Workflow(graph=graph, debug=False)


# ============================================================
# 第二區：事件處理函式
# ============================================================
# 這裡的函式會被下面第三區的 @cl.on_chat_start / @cl.on_message 呼叫。


def convert_table_name(filename: str) -> str:
    """把上傳的 CSV 檔名轉換成合法、安全的 SQL 表名。"""

    name = filename.rsplit(".", 1)[0]
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = name.strip("_")
    if not name or name[0].isdigit():
        name = f"table_{name}"

    return name


async def upload_csv(
    csv_path: str,
    thread_id: str,
    table_names: list[str],
) -> tuple[str, list[str]]:
    """使用者附加 CSV 後執行：寫進這個 thread 專屬的資料庫，回傳通知文字與累積後的表名清單。"""

    session_workspace = f".data/{thread_id}"
    database_path = f"{session_workspace}/data.db"
    os.makedirs(session_workspace, exist_ok=True)

    filename = os.path.basename(csv_path)
    table_name = convert_table_name(filename)

    with duckdb.connect(database_path) as connection:
        connection.execute(
            f"CREATE OR REPLACE TABLE {table_name} AS "
            f"SELECT * FROM read_csv_auto(?)",
            [csv_path],
        )

    table_names = table_names + [table_name]

    notice = Template("已上傳「$filename」，存成資料表「$table_name」")
    return notice.substitute(filename=filename, table_name=table_name), table_names


async def reply_message(
    user_message: str,
    thread_id: str,
    table_names: list[str],
) -> None:
    """使用者送出文字訊息後執行：呼叫 Workflow.stream()，把執行過程逐步呈現在畫面上。

    跟 Gradio 版本不同，這裡不需要自己組 chat_history 陣列——每次
    cl.Message(...).send() 就會直接送出一則新的對話訊息,由 Chainlit 接手顯示。
    """

    session_workspace = f".data/{thread_id}"
    database_path = f"{session_workspace}/data.db"

    async for event in workflow.stream(
        thread_id=thread_id,
        session_workspace=session_workspace,
        database_path=database_path,
        table_names=table_names,
        user_message=user_message,
    ):
        if event["level"] == "tool_call":
            content = f"🔧 呼叫工具：{event['tool_name']}"
        elif event["level"] == "tool_result":
            content = f"✅ 工具結果：{event['content']}"
        elif event["level"] == "node" and event["content"]:
            content = event["content"]
        else:
            continue

        await cl.Message(content=content).send()


# ============================================================
# 第三區：Chainlit 事件綁定
# ============================================================
# Chainlit 沒有 Gradio 的「畫面排版」區塊——聊天視窗是內建的,不用自己排版、
# 也不用手動接 inputs/outputs,直接用裝飾器把函式接到生命週期事件上就好。


@cl.on_chat_start
async def initialize_session() -> None:
    """對話開始時執行一次：組出這個 session 專屬的 thread_id，並顯示歡迎訊息。"""

    thread_id = cl.context.session.id
    cl.user_session.set("thread_id", thread_id)
    cl.user_session.set("table_names", [])

    await cl.Message(content=f"本次對話的 thread_id：{thread_id}").send()


@cl.on_message
async def handle_message(message: cl.Message) -> None:
    """使用者送出訊息（可能附帶 CSV 檔案，也可能只有文字）後執行。"""

    thread_id = cl.user_session.get("thread_id")
    table_names = cl.user_session.get("table_names")

    csv_elements = [
        element
        for element in message.elements
        if element.path and element.name.lower().endswith(".csv")
    ]
    for element in csv_elements:
        notice, table_names = await upload_csv(element.path, thread_id, table_names)
        cl.user_session.set("table_names", table_names)
        await cl.Message(content=notice).send()

    user_message = message.content.strip()
    if not user_message:
        return

    await reply_message(user_message, thread_id, table_names)


# ============================================================
# 第四區：啟動伺服器
# ============================================================
# Chainlit 不像 Gradio 需要在檔案裡寫 launch()，而是用指令啟動：
#     chainlit run websites/service_with_chainlit.py -w
