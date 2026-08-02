import sys
import tempfile
import uuid
from pathlib import Path

import chainlit as cl

sys.path.append(str(Path(__file__).resolve().parent.parent))

from agenticend.agent import stream as agent_stream


WELCOME_MESSAGE = (
    "你好，我是資料分析助理。\n\n"
    "把 CSV 檔案拖進來（可以一次選多個），或直接跟我聊聊你想做的分析。\n\n"
    "＿目前這是介面骨架，還沒接上真正的分析邏輯，訊息會先用假回應頂著。＿"
)


@cl.on_chat_start
async def on_chat_start():
    # 模擬登入後已知的使用者身分，先寫死，之後接真的認證再換掉這裡。
    user_id = "anonymous"
    thread_id = str(uuid.uuid4())
    workspace = f".data/{user_id}/{thread_id}"

    cl.user_session.set("user_id", user_id)
    cl.user_session.set("thread_id", thread_id)
    cl.user_session.set("workspace", workspace)

    # 悄悄把 workspace 資訊送進這個 thread 的對話歷史，
    # 讓 LLM 之後每一輪都能在上下文裡看到，不顯示給使用者看。
    seed_message = (
        f"系統資訊：這個對話的資料工作目錄（workspace）是 {workspace}，"
        "之後儲存或查詢資料時請使用這個路徑。"
    )
    async for token in agent_stream(thread_id, seed_message):
        print(token, end="", flush=True)

    await cl.Message(content=WELCOME_MESSAGE).send()


@cl.on_message
async def on_message(user_message: cl.Message):

    # 檢查是否帶表格檔案，帶檔案預先備份到資料庫，
    # 如果上傳非表格檔案，暫時不處理。
    if is_files_in_user_message(user_message):
        create_database(database_path)
        for file_name in get_file_names(user_message):
            if 'csv' not in file_name:
                print('目前只處理 csv')
                print(f'先略 {file_name}')
                continue
            create_table_with_file_name(database_path, table_name, file_name)
            save_table_file
        workspace
        thread_id
        
        write_table_content_to
    csv_files = [
        element
        for element in user_message.elements
        if (element.name or "").lower().endswith(".csv")
    ]

    if csv_files:
        names = "、".join(f.name for f in csv_files)
        await cl.Message(
            content=f"收到 {len(csv_files)} 個檔案：{names}\n（stub：尚未實際存進 workspace 或分析）"
        ).send()
        return

    if "下載" in user_message.content or "download" in user_message.content.lower():
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            f.write("col_a,col_b\n1,2\n3,4\n")
            stub_path = f.name

        await cl.Message(
            content="這是一個假的分析結果，示範下載流程用：",
            elements=[cl.File(name="result.csv", path=stub_path, display="inline")],
        ).send()
        return

    reply = cl.Message(content="")
    await reply.send()

    thread_id = cl.user_session.get("thread_id")
    callback_handler = cl.AsyncLangchainCallbackHandler()
    async for token in agent_stream(
        thread_id, user_message.content, callbacks=[callback_handler]
    ):
        await reply.stream_token(token)

    await reply.update()
