import asyncio
import uuid

from langchain_core.messages import HumanMessage

from main import build_workflow
from nodes.orchestration import OrchestrationState


async def main() -> bool:
    """讓使用者在終端機裡連續提問，同一個 thread_id 讓對話歷史被 checkpointer 保留下來。"""

    workflow = build_workflow()

    config = {
        "configurable": {
            "thread_id": "666",
            "workspace": '.data/G72602/workspace/' + uuid.uuid4().hex[:6],
        }
    }

    print("輸入問題開始對話，輸入 exit 離開。")

    while True:
        question = input("\n你：").strip()
        if question.lower() in ("exit", "quit"):
            break
        if not question:
            continue

        state = OrchestrationState(messages=[HumanMessage(question)], next=None)
        result = await workflow.ainvoke(state, config)

        for message in result["messages"]:
            message.pretty_print()

    return True


if __name__ == "__main__":
    asyncio.run(main())
