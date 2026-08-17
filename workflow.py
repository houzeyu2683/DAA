import logging
import os
from collections.abc import Iterator

import dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain_core.messages import AIMessageChunk, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

logging.basicConfig(
    level=logging.INFO,
    handlers=[
        # logging.StreamHandler(),            # 印到 console
        logging.FileHandler("workflow.log"), # 同時寫進檔案
    ],
)
logger = logging.getLogger(__name__)


dotenv.load_dotenv()



@tool
def list_files() -> str:
    """列出這個 session 底下已上傳的檔案（假資料，測試用）。"""
    return f"fake_file_1.txt, fake_file_2.csv"

@tool
def write_file(file_name: str, content: str) -> str:
    """寫入一個檔案（假資料，測試用，不會真的寫入）。"""
    return f"pretend wrote {file_name}: {content[:20]}"

@tool
def delete_file(file_name: str) -> str:
    """刪除一個檔案（假資料，測試用，不會真的刪除）。"""
    return f"pretend deleted {file_name}"


model = ChatOpenAI(
    model=os.environ["MODEL_NAME"],
    base_url=os.environ["MODEL_URL"],
    api_key=os.environ["MODEL_KEY"],
    temperature=0,
)
checkpointer = InMemorySaver()
compiled_agent = create_agent(
    model,
    [list_files, write_file, delete_file],
    checkpointer=checkpointer,
    # middleware=[HumanInTheLoopMiddleware(interrupt_on={"write_file": True, "delete_file": True})],
)



class Assistant:

    # def __init__(self, compiled_agent: CompiledStateGraph, thread_id: str) -> None:
    def __init__(self, thread_id: str) -> None:
        # self.compiled_agent = compiled_agent
        self.thread_id = thread_id
        self.config = {"configurable": {"thread_id": thread_id}}
        return
    

    def respond_streaming(self, request_input: str | Command) -> Iterator[dict]:
        """
        餵一次輸入進 graph.stream(...)，消化這一輪的原始事件，
        yield 出結構化的事件字典，呼叫端自己決定怎麼呈現、要不要重試。

        request_input 有兩種可能：
          - str：一般的使用者輸入文字，這裡會包成 HumanMessage 再送進 graph.stream。
          - Command：用來「恢復」被 interrupt() 中斷的執行。

        中斷了要不要重新呼叫、怎麼問人類——這裡完全不管，交給呼叫端
        （main.py）自己決定，這裡只負責跑一次、把事件吐出去。
        """
        logger.info("respond_streaming start: input_type=%s", type(request_input).__name__)

        if isinstance(request_input, str):
            state = {"messages": [HumanMessage(content=request_input)]}
        else:
            state = request_input

        for mode, data in compiled_agent.stream(
            state,
            config=self.config,
            stream_mode=["updates", "messages"],
        ):
            if mode == "updates":
                yield from self.handle_updates(data)
            elif mode == "messages":
                yield from self.handle_messages(data)

        logger.info("respond_streaming done")

    def handle_updates(self, data: dict) -> Iterator[dict]:
        """
        updates 模式：每個節點「跑完」才會給一次事件，內容是完整訊息（不是逐字片段）。

        判斷「這是不是工具結果」不能只看 node_name == "tools"——
        human-in-the-loop 拒絕某個工具呼叫時，middleware 會自己合成一則 ToolMessage
        塞進對話歷史，來源節點是 "HumanInTheLoopMiddleware.after_model" 不是 "tools"，
        改成直接看訊息型別（是不是 ToolMessage）才不會漏接。
        """

        # if "__interrupt__" in data:
        #     interrupt = data["__interrupt__"][0]
        #     logger.info("interrupt: id=%s request=%s", interrupt.id, interrupt.value)
        #     yield {
        #         "type": "interrupt",
        #         "request": interrupt.value,
        #         "id": interrupt.id,
        #     }
        #     return

        for _, node_update in data.items():
            # _ = node_name
            if not node_update:
                continue
            for message in node_update.get("messages", []):
                if isinstance(message, ToolMessage):
                    logger.info(
                        "tool_result: name=%s tool_call_id=%s",
                        message.name,
                        message.tool_call_id,
                    )
                    yield {
                        "type": "tool_result",
                        "name": message.name,
                        "content": message.content,
                        "tool_call_id": message.tool_call_id,
                    }
                elif getattr(message, "tool_calls", None):
                    for tool_call in message.tool_calls:
                        logger.info(
                            "tool_call: name=%s args=%s id=%s",
                            tool_call["name"],
                            tool_call["args"],
                            tool_call["id"],
                        )
                        yield {
                            "type": "tool_call",
                            "name": tool_call["name"],
                            "args": tool_call["args"],
                            "id": tool_call["id"],
                        }

    def handle_messages(self, data: tuple) -> Iterator[dict]:
        """
        messages 模式：模型每產生一個 token 就會 yield 一次，
        用來做「最終回覆文字」的逐字串流效果。
        只挑 AIMessageChunk 且有內容的 chunk，排除工具呼叫過程中的空 chunk。
        """
        chunk, _ = data
        if isinstance(chunk, AIMessageChunk) and chunk.content:
            logger.debug("text_chunk: content=%r", chunk.content)
            yield {"type": "text_chunk", "content": chunk.content}


if __name__ == "__main__":
    assistant = Assistant(thread_id="test-thread-1")

    for event in assistant.respond_streaming("幫我列出目前有哪些檔案，然後寫一個 hello.txt，內容是 hello world"):
        event_type = event["type"]
        if event_type == "tool_call":
            print(f"\n[tool_call] {event['name']}({event['args']})")
        elif event_type == "tool_result":
            print(f"[tool_result] {event['name']} -> {event['content']}")
        elif event_type == "text_chunk":
            print(event["content"], end="", flush=True)
    print()
