import os
import shutil

import gradio as gr

from workflow import Assistant


def get_session_id(request: gr.Request) -> str:
    # gr.Request is auto-injected by Gradio
    # based on the type hint, not passed via `inputs`.
    return request.session_hash


def handle_message(message: str, history: list, session_id: str):
    if not message:
        return

    history = history + [{"role": "user", "content": message}]
    yield history, ""

    assistant = Assistant(thread_id=session_id)
    text_message = None  # 目前正在累積的那則助理文字訊息，遇到工具事件就重置
    tool_messages = {}  # tool_call_id -> 對應的那則訊息字典，等結果回來時原地更新

    for event in assistant.respond_streaming(message):
        event_type = event["type"]

        if event_type == "tool_call":
            tool_message = {
                "role": "assistant",
                "content": f"參數：{event['args']}",
                "metadata": {"title": f"🔧 呼叫 {event['name']}", "status": "pending"},
            }
            tool_messages[event["id"]] = tool_message
            history.append(tool_message)
            text_message = None
            yield history, ""

        elif event_type == "tool_result":
            tool_message = tool_messages.get(event["tool_call_id"])
            if tool_message is not None:
                tool_message["content"] += f"\n結果：{event['content']}"
                tool_message["metadata"]["status"] = "done"
            text_message = None
            yield history, ""

        elif event_type == "text_chunk":
            if text_message is None:
                text_message = {"role": "assistant", "content": ""}
                history.append(text_message)
            text_message["content"] += event["content"]
            yield history, ""

def handle_file_upload(file_paths: list[str], session_id: str) -> str:
    session_dir = os.path.join(".upload", session_id)
    os.makedirs(session_dir, exist_ok=True)

    saved_paths = []
    for file_path in file_paths:
        dest_path = os.path.join(session_dir, os.path.basename(file_path))
        shutil.copy(file_path, dest_path)
        saved_paths.append(dest_path)

    return "\n".join(saved_paths)


with gr.Blocks() as demo:

    with gr.Group():
        session_id_output = gr.Textbox(label="Session ID", interactive=False)
        file_path_output = gr.Textbox(label="Saved File Paths", interactive=False)

    # Triggers once when the page loads, to populate session_id_output.
    demo.load(get_session_id, inputs=None, outputs=session_id_output)

    file_input = gr.File(label="Upload Files", file_count="multiple", height=120)

    file_input.upload(
        handle_file_upload, 
        inputs=[file_input, session_id_output], 
        outputs=file_path_output
    )

    chatbot = gr.Chatbot(label="Chat")
    with gr.Row():
        message_input = gr.Textbox(label="Message", placeholder="輸入訊息...", scale=8)
        send_button = gr.Button("Send", scale=1)

    message_input.submit(
        handle_message,
        inputs=[message_input, chatbot, session_id_output],
        outputs=[chatbot, message_input],
    )
    send_button.click(
        handle_message,
        inputs=[message_input, chatbot, session_id_output],
        outputs=[chatbot, message_input],
    )

if __name__ == "__main__":
    demo.launch()
