import gradio as gr
import os
from string import Template

from agent import workflow as agent


# ============================================================
# 第一區：事件處理函式
# ============================================================
# 這裡的函式會被下面畫面上的按鈕、輸入框呼叫。


def initialize_session(request: gr.Request) -> tuple[str, list[dict]]:
    """頁面載入時執行一次：組出這個分頁專屬的 thread_id，並顯示歡迎訊息。"""

    thread_id = request.session_hash
    welcome_message = {
        "role": "assistant",
        "content": f"本次對話的 thread_id：{thread_id}",
    }
    return thread_id, [welcome_message]


def set_workspace(folder_path: str, chat_history: list[dict]) -> list[dict]:
    """按下「設定工作資料夾」後執行：把提示訊息加進聊天紀錄。"""

    if folder_path == "" or not os.path.isdir(folder_path):
        message = {"role": "assistant", "content": "請先輸入資料夾路徑"}
        return chat_history + [message]

    workspace_information = Template("助理將專注在「$folder_path」底下進行工作")
    message = {
        "role": "assistant",
        "content": workspace_information.substitute(folder_path=folder_path),
    }
    return chat_history + [message]


def reply_message(user_message: str, chat_history: list[dict], thread_id: str):
    """使用者送出訊息後執行：呼叫 agent.py 裡的 agent，把執行過程逐步呈現在畫面上。

    這是一個 generator（用 yield 而不是 return）：Gradio 看到 fn 是 generator，
    會在每次 yield 的時候就把畫面更新一次，讓使用者看得到「現在在呼叫哪個工具」
    「工具結果」這些中間過程，不用整輪跑完才看到東西。
    """

    chat_history = chat_history + [{"role": "user", "content": user_message}]
    yield chat_history, ""

    # thread_id 決定 agent 要用哪一份對話記憶（同一個分頁的 thread_id 都一樣，
    # 所以同一個分頁裡的對話可以接續，不同分頁彼此不會混在一起）。
    config = {"configurable": {"thread_id": thread_id}}

    # stream_mode="updates" 每次吐出「某個節點跑完後新增了哪些完整訊息」，
    # 不是逐字的 token，所以不會遇到 AIMessageChunk / AIMessage 混雜的問題。
    for update in agent.stream(
        {"messages": [{"role": "user", "content": user_message}]},
        config=config,
        stream_mode="updates",
    ):
        for node_output in update.values():
            for message in node_output["messages"]:
                if message.type == "ai" and message.tool_calls:
                    for call in message.tool_calls:
                        content = f"🔧 呼叫工具：{call['name']}"
                        chat_history = chat_history + [
                            {"role": "assistant", "content": content}
                        ]
                        yield chat_history, ""
                elif message.type == "tool":
                    content = f"✅ 工具結果：{message.content}"
                    chat_history = chat_history + [
                        {"role": "assistant", "content": content}
                    ]
                    yield chat_history, ""
                elif message.type == "ai" and message.content:
                    chat_history = chat_history + [
                        {"role": "assistant", "content": message.content}
                    ]
                    yield chat_history, ""


# ============================================================
# 第二區：畫面排版
# ============================================================
# with gr.Blocks(...) 裡面的元件，會照寫的順序由上而下排列。

with gr.Blocks(title="資料分析助理") as block:
    gr.Markdown("## 資料分析助理")

    thread_id_state = gr.State()  # 不會顯示在畫面上，只是存這個分頁的 thread_id

    with gr.Row():
        folder_path_input_box = gr.Textbox(
            label="專案資料夾路徑",
            placeholder="輸入本地端的資料夾路徑，例如 /home/user/project",
            scale=4,
        )
        set_workspace_button = gr.Button("設定工作資料夾", scale=1)

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
    # 第三區：事件綁定
    # ------------------------------------------------------------
    # 把上面的元件跟第一區的函式接起來。
    # fn = 要呼叫的函式，inputs = 傳給函式的參數，outputs = 函式回傳值要寫回哪些元件。

    block.load(
        fn=initialize_session,
        inputs=None,
        outputs=[thread_id_state, chat_output_block],
    )

    set_workspace_button.click(
        fn=set_workspace,
        inputs=[folder_path_input_box, chat_output_block],
        outputs=[chat_output_block],
    )

    user_message_input_box.submit(
        fn=reply_message,
        inputs=[user_message_input_box, chat_output_block, thread_id_state],
        outputs=[chat_output_block, user_message_input_box],
    )
    send_message_button.click(
        fn=reply_message,
        inputs=[user_message_input_box, chat_output_block, thread_id_state],
        outputs=[chat_output_block, user_message_input_box],
    )


# ============================================================
# 第四區：啟動伺服器
# ============================================================
if __name__ == "__main__":
    block.launch()
