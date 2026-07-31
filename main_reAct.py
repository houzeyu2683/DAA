import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.callbacks import get_usage_metadata_callback

from tools.system import (
    is_file_exist,
    is_folder_exist,
    list_file_names,
    list_folder_names,
    search_file_names,
    search_file_names_with_regular_expression,
    read_file_content,
    create_folder,
    create_file,
    write_content_in_file,
    view_image,
)
from tools.program import search_code_in_file


class LoggingSummarizationMiddleware(SummarizationMiddleware):
    """在原本 SummarizationMiddleware 的基礎上，觸發摘要時額外印出提示訊息。"""

    def before_model(self, state, runtime):
        result = super().before_model(state, runtime)
        if result is not None:
            print("\n[SummarizationMiddleware 已觸發，對話歷史已被摘要]")
        return result

    async def abefore_model(self, state, runtime):
        result = await super().abefore_model(state, runtime)
        if result is not None:
            print("\n[SummarizationMiddleware 已觸發，對話歷史已被摘要]")
        return result


load_dotenv(Path(__file__).parent / ".env")

model = ChatOpenAI(
    model=os.environ["MODEL_NAME"],
    base_url=os.environ["MODEL_URL"],
    api_key=os.environ["MODEL_KEY"],
    temperature=0,
    extra_body={"reasoning": {"enabled": False}}
    # model_kwargs={"parallel_tool_calls": False},
    # OpenRouter 會把同一個模型路由到多家 provider，若選到的 provider
    # 不支援圖片輸入就會 404。gemma-4-26b-a4b-it 目前只有 Google 自己
    # 上架的 endpoint 看起來有完整支援圖片，所以指定路由過去。
    # extra_body={"provider": {"order": ["Google"]}},
)

tools = [
    is_file_exist,
    is_folder_exist,
    list_file_names,
    list_folder_names,
    search_file_names,
    search_file_names_with_regular_expression,
    read_file_content,
    create_folder,
    create_file,
    write_content_in_file,
    view_image,
    search_code_in_file,
]

agent = create_agent(
    model,
    tools=tools,
    middleware=[
        LoggingSummarizationMiddleware(
            model=model,
            trigger=("tokens", 40000),
            keep=("messages", 20),
        ),
    ],
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

        with get_usage_metadata_callback() as usage_callback:
            response = agent.invoke(
                {"messages": [{"role": "user", "content": user_input}]},
                config=config,
            )

        for message in response["messages"][prev_len:]:
            message.pretty_print()
        prev_len = len(response["messages"])
        print(f"\n[token 用量] {usage_callback.usage_metadata}")
