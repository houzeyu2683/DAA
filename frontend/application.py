import sys
import tempfile
import uuid
import chainlit as cl
import dotenv 
import os


from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableConfig
from string import Template
from pathlib import Path
from langchain_core.messages import SystemMessage, HumanMessage


from agenticend import workflow
from frontend.utilities import (
    is_files_in_user_message,
    # get_file_names,
    create_database,
    create_table_with_file_path,
)

sys.path.append(str(Path(__file__).resolve().parent.parent))


agent = workflow.get_agent()


@cl.on_chat_start
async def on_chat_start():
    
    # 模擬登入後已知的使用者身分，先寫死，之後接真的認證再換掉這裡。
    user_id = "G72602"
    thread_id = uuid.uuid4().hex[0:4]
    # chat_workspace = f".data/{user_id}/{thread_id}"

    #
    user_information = Template(
        "用戶基本資訊：\n"
        "user_id: $user_id\n"
        "thread_id: $thread_id\n"
        # "chat_workspace: $chat_workspace\n"
        '\n'
        "接下來的對話中，如果涉及儲存或查詢資料時請參考這些資訊。"
    ).substitute(
        user_id=user_id,
        thread_id=thread_id,
        # chat_workspace=chat_workspace
    )

    #
    
    messages = {"messages": [SystemMessage(content=user_information)]}
    config={
        "configurable": {
            'user_id': user_id,
            'thread_id': thread_id,
            # 'chat_workspace': chat_workspace
        }
    }
    response = await agent.ainvoke(messages, config=config)
    response["messages"][-1].pretty_print()

    #
    cl.user_session.set('config', config)
    
    #
    wellcome_message = (
        "你好，我是你的資料分析助理，"
        "請把 CSV 檔案拖進來，讓我協助你或做分析。"
    )
    await cl.Message(content=wellcome_message).send()


@cl.on_message
async def on_message(user_message: cl.Message):

    config = cl.user_session.get('config')
    
    # 檢查是否帶檔案。
    if is_files_in_user_message(user_message):
        user_id = config.get("configurable").get('user_id')
        thread_id = config.get("configurable").get('thread_id')
        database_path = os.path.join(
            '.data', user_id, thread_id, 'database.db'
        )
        create_database(database_path)
        saved_file_names, saved_table_names = [], []
        saved_total = 0
        for element in user_message.elements:
            file_path, file_name = element.path, element.name
            if 'csv' not in file_name:
                continue
            # file_name = 'fifa_world_cup_2026_player_performance.csv'
            table_name = Path(file_name).stem.replace(' ', '_').lower()
            create_table_with_file_path(database_path, table_name, file_path)
            saved_file_names.append(file_name)
            saved_table_names.append(table_name)
            saved_total += 1
            continue
        await cl.Message(content=f"已存入 {saved_total} 個 CSV 檔").send()

        if saved_total>0:
            # 把上傳結果也告訴模型，讓它之後回答時知道有這些資料表可用。
            file_names = ",".join(saved_file_names)
            table_names = ",".join(saved_table_names)
            file_information = Template(
                "系統資訊：\n"
                "使用者上傳 CSV 檔案：$file_names\n"
                "資料庫位置：$database_path\n"
                "對應資料表名稱：$table_names\n"
                "\n"
                "之後若使用者提到這些資料，請參考這份資訊。"
            ).substitute(
                file_names=file_names,
                database_path=database_path,
                table_names=table_names,
            )
            messages = {
                "messages": [SystemMessage(content=file_information)]
            }
            response = await agent.ainvoke(
                messages,
                config=config,
            )
            response["messages"][-1].pretty_print()

    # 處理單純文字
    messages = {"messages": [HumanMessage(content=user_message.content)]}

    reply = cl.Message(content="")
    await reply.send()

    astream = agent.astream(
        messages,
        config=config,
        stream_mode="messages"
    )
    async for chunk, _ in astream:
        if chunk.content:
            await reply.stream_token(chunk.content)

    await reply.update()
