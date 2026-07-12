"""Minimal, runnable demo of AgentMiddleware.before_model — no DuckDB, no MCP.

Run it and read the printed lines. You should see:
  1. before_model fires more than once per single agent.invoke() call
     (once before every LLM call, including the one after a tool result
     comes back).
  2. It's plain, synchronous Python — no LLM involved in the decision.
  3. An in-memory cache (`self.greeted_names`) turns repeat firings on the
     same input into no-ops, same pattern as `_ingested_paths` in the real
     CsvIngestMiddleware.

This mirrors agent/middleware.py's CsvIngestMiddleware, but detects a name
("我是XXX") instead of a CSV path, and has nothing to await, so it uses a
plain `def before_model` instead of `async def abefore_model`.
"""

import os
import re

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware, AgentState
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage
from langchain_core.tools import tool
from langgraph.runtime import Runtime

load_dotenv()

model = init_chat_model(
    model=os.environ["MODEL_NAME"],
    model_provider="openai",
    base_url=os.environ["MODEL_URL"],
    api_key=os.environ["API_KEY"],
    temperature=0,
)


@tool
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


class NameDetectMiddleware(AgentMiddleware):
    """Deterministically detects '我是XXX' and injects a SystemMessage.

    Same shape as CsvIngestMiddleware: regex over the latest human message,
    skip anything already handled, mutate state via a returned dict.
    """

    def __init__(self):
        self.call_count = 0
        self.greeted_names: set[str] = set()

    def before_model(self, state: AgentState, runtime: Runtime) -> dict | None:
        self.call_count += 1
        print(f"\n[before_model] fired — LLM call #{self.call_count} is about to happen")

        last_human = next(
            (m for m in reversed(state["messages"]) if m.type == "human"), None
        )
        if last_human is None or not isinstance(last_human.content, str):
            print("[before_model] no human text found, doing nothing")
            return None

        match = re.search(r"我是\s*([^\s,，。]+)", last_human.content)
        if not match:
            print("[before_model] no '我是XXX' pattern found, doing nothing")
            return None

        name = match.group(1)
        if name in self.greeted_names:
            print(f"[before_model] '{name}' already handled earlier — no-op (cache hit)")
            return None

        print(f"[before_model] NEW name detected: '{name}' -> injecting a SystemMessage")
        self.greeted_names.add(name)
        return {
            "messages": [
                SystemMessage(content=f"[系統自動偵測] 使用者名字是 {name}，回覆時請稱呼他的名字。")
            ]
        }


def main() -> None:
    middleware = NameDetectMiddleware()
    agent = create_agent(
        model,
        tools=[add],
        system_prompt="你是一個助理，若被要求算加法就呼叫 add 工具。",
        middleware=[middleware],
    )

    result = agent.invoke(
        {"messages": [{"role": "user", "content": "我是Andy，請幫我算 3 加 5"}]}
    )

    print("\n=== 最終回答 ===")
    print(result["messages"][-1].content)
    print(f"\n=== before_model 總共被觸發 {middleware.call_count} 次 ===")


if __name__ == "__main__":
    main()
