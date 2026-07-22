import os
import uuid
from collections.abc import Callable

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_tool_call
from langchain.messages import ToolMessage
from langchain.tools.tool_node import ToolCallRequest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from tools.default_tools import (
    is_file_exist,
    create_database,
    create_table,
    is_columns_exist,
    select_columns,
    preview_table,
    export_table,
    show_image,
    send_email
)


load_dotenv()

model = ChatOpenAI(
    model=os.environ["MODEL_NAME"],
    base_url=os.environ["MODEL_URL"],
    api_key=os.environ["MODEL_KEY"],
    temperature=0,
    model_kwargs={"parallel_tool_calls": False},
)

tools = [
    is_file_exist,
    create_database,
    create_table,
    is_columns_exist,
    select_columns,
    preview_table,
    export_table,
    show_image,
    send_email
]

# create_agent 預設只攔截「參數格式錯誤」，工具執行期間真正丟出的例外（例如查詢
# 不存在的資料表、程式碼執行出錯）不會被接住，會讓整個 agent.invoke() 直接崩潰。
# 這個 middleware 統一包一層 try/except：所有工具呼叫都會先經過這裡，
# 出錯就轉成一則錯誤訊息回傳給 model，讓它自己看得懂錯誤、有機會修正重試，
# 而不是讓整個對話當掉。寫在這裡一次，就不用在每個工具函式裡各自重複同樣的邏輯。
@wrap_tool_call
def handle_tool_errors(
    request: ToolCallRequest,
    handler: Callable[[ToolCallRequest], ToolMessage | Command],
) -> ToolMessage | Command:
    try:
        return handler(request)
    except Exception as e:
        return ToolMessage(
            tool_call_id=request.tool_call["id"],
            content=f"Tool execution failed: {e}",
            is_error=True,
        )


agent = create_agent(
    model,
    tools=tools,
    middleware=[handle_tool_errors],
    checkpointer=InMemorySaver(),
)

config = {"configurable": {"thread_id": str(uuid.uuid4())}}


if __name__ == "__main__":
    print("多輪對話測試，輸入 exit 離開。")
    prev_len = 0
    while True:
        user_input = input("\n你: ")
        if user_input.strip().lower() in {"exit", "quit"}:
            break

        response = agent.invoke(
            {"messages": [{"role": "user", "content": user_input}]},
            config=config,
        )

        while "__interrupt__" in response:
            payload = response["__interrupt__"][0].value
            print(f"\n[需要確認] {payload}")
            answer = input("你的回覆: ")
            response = agent.invoke(Command(resume=answer), config=config)

        for message in response["messages"][prev_len:]:
            message.pretty_print()
        prev_len = len(response["messages"])
