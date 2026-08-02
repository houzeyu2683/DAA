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
    cl.user_session.set("thread_id", str(uuid.uuid4()))
    await cl.Message(content=WELCOME_MESSAGE).send()


@cl.on_message
async def on_message(message: cl.Message):
    csv_files = [
        element
        for element in message.elements
        if (element.name or "").lower().endswith(".csv")
    ]

    if csv_files:
        names = "、".join(f.name for f in csv_files)
        await cl.Message(
            content=f"收到 {len(csv_files)} 個檔案：{names}\n（stub：尚未實際存進 workspace 或分析）"
        ).send()
        return

    if "下載" in message.content or "download" in message.content.lower():
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
    async for token in agent_stream(thread_id, message.content):
        await reply.stream_token(token)

    await reply.update()
