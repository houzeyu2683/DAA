import os
import re
from string import Template

import duckdb
import gradio as gr

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
# 這裡的函式會被下面畫面上的按鈕、輸入框呼叫。


def build_table_name(filename: str) -> str:
    """把上傳的 CSV 檔名轉換成合法、安全的 SQL 表名。"""

    name = filename.rsplit(".", 1)[0]
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = name.strip("_")
    if not name or name[0].isdigit():
        name = f"table_{name}"
    return name


def initialize_session(request: gr.Request) -> tuple[str, list[dict], list[str]]:
    """頁面載入時執行一次：組出這個分頁專屬的 thread_id，並顯示歡迎訊息。"""

    thread_id = request.session_hash
    welcome_message = {
        "role": "assistant",
        "content": f"本次對話的 thread_id：{thread_id}",
    }
    return thread_id, [welcome_message], []


def upload_csv(
    csv_path: str,
    chat_history: list[dict],
    thread_id: str,
    table_names: list[str],
) -> tuple[list[dict], list[str]]:
    """使用者上傳 CSV 後執行：寫進這個 thread 專屬的資料庫，累積表名清單。"""

    if not csv_path:
        return chat_history, table_names

    session_workspace = f".data/{thread_id}"
    database_path = f"{session_workspace}/data.db"
    os.makedirs(session_workspace, exist_ok=True)

    filename = os.path.basename(csv_path)
    table_name = build_table_name(filename)

    with duckdb.connect(database_path) as connection:
        connection.execute(
            f"CREATE OR REPLACE TABLE {table_name} AS "
            f"SELECT * FROM read_csv_auto(?)",
            [csv_path],
        )

    table_names = table_names + [table_name]

    notice = Template("已上傳「$filename」，存成資料表「$table_name」")
    message = {
        "role": "assistant",
        "content": notice.substitute(filename=filename, table_name=table_name),
    }
    return chat_history + [message], table_names


async def reply_message(
    user_message: str,
    chat_history: list[dict],
    thread_id: str,
    table_names: list[str],
):
    """使用者送出訊息後執行：呼叫 Workflow.stream()，把執行過程逐步呈現在畫面上。

    這是一個 async generator（用 yield 而不是 return）：Gradio 看到 fn 是
    generator，會在每次 yield 的時候就把畫面更新一次，讓使用者看得到「現在在
    呼叫哪個工具」「工具結果」這些中間過程，不用整輪跑完才看到東西。
    """

    chat_history = chat_history + [{"role": "user", "content": user_message}]
    yield chat_history, ""

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

        chat_history = chat_history + [{"role": "assistant", "content": content}]
        yield chat_history, ""


# ============================================================
# 第三區：畫面排版
# ============================================================
# with gr.Blocks(...) 裡面的元件，會照寫的順序由上而下排列。

with gr.Blocks(title="資料分析助理") as block:
    gr.Markdown("## 資料分析助理")

    thread_id_state = gr.State()  # 不會顯示在畫面上，只是存這個分頁的 thread_id
    table_names_state = gr.State([])  # 累積這個 thread 已經上傳過的表名

    csv_upload_box = gr.File(label="上傳 CSV", file_types=[".csv"])

    chat_output_block = gr.Chatbot(label="對話", height=500)

    with gr.Row():
        user_message_input_box = gr.Textbox(
            label="訊息",
            placeholder="輸入訊息後按 Enter 或點送出",
            scale=4,
            show_label=False,
        )
        send_message_button = gr.Button("送出", scale=1)

    # ------------------------------------------------------------
    # 第四區：事件綁定
    # ------------------------------------------------------------
    # 把上面的元件跟第二區的函式接起來。
    # fn = 要呼叫的函式，inputs = 傳給函式的參數，outputs = 函式回傳值要寫回哪些元件。

    block.load(
        fn=initialize_session,
        inputs=None,
        outputs=[thread_id_state, chat_output_block, table_names_state],
    )

    csv_upload_box.upload(
        fn=upload_csv,
        inputs=[csv_upload_box, chat_output_block, thread_id_state, table_names_state],
        outputs=[chat_output_block, table_names_state],
    )

    user_message_input_box.submit(
        fn=reply_message,
        inputs=[user_message_input_box, chat_output_block, thread_id_state, table_names_state],
        outputs=[chat_output_block, user_message_input_box],
    )
    send_message_button.click(
        fn=reply_message,
        inputs=[user_message_input_box, chat_output_block, thread_id_state, table_names_state],
        outputs=[chat_output_block, user_message_input_box],
    )


# ============================================================
# 第五區：啟動伺服器
# ============================================================
if __name__ == "__main__":
    block.launch()
