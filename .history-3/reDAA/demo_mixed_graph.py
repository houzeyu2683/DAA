"""Minimal, runnable demo of "混用": create_agent nested inside a hand-built
StateGraph.

The scenario is something AgentMiddleware genuinely CANNOT do: skip calling
the LLM entirely for some inputs. Middleware hooks (before_model/after_model)
always run *around* an actual model call -- they can't decide "don't call the
model at all this time". A hand-built graph can, because routing happens
*before* you even reach the node that calls a model.

Graph shape:

    START --> router --+-- "greeting" --> greeting_node (plain Python, no LLM) --> END
                        |
                        +-- "math"     --> math_agent (a normal create_agent) --> END

- `router`: plain Python, decides which branch, no LLM call.
- `greeting_node`: plain Python, canned reply, no LLM call.
- `math_agent`: an ordinary create_agent(...) ReAct agent, used as ONE NODE
  inside the bigger hand-built graph -- this is the "mixed use" part.
"""

import os
from typing import Literal

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import Annotated, TypedDict

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


# ---- the create_agent part: a normal ReAct agent, later used as ONE node ----
math_agent = create_agent(
    model,
    tools=[add],
    system_prompt="你是一個算術助理，用 add 工具回答加法問題。",
)


class GraphState(TypedDict):
    messages: Annotated[list, add_messages]


# ---- the hand-built StateGraph part ----
def router(state: GraphState) -> Literal["greeting_node", "math_agent"]:
    last = state["messages"][-1]
    text = last.content if isinstance(last.content, str) else ""
    print(f"[router] plain Python, no LLM call — inspecting: {text!r}")
    if any(g in text for g in ("你好", "哈囉", "hi", "hello")):
        print("[router] -> greeting_node (LLM will NOT be called)")
        return "greeting_node"
    print("[router] -> math_agent (LLM WILL be called)")
    return "math_agent"


def greeting_node(state: GraphState) -> dict:
    print("[greeting_node] plain Python, no LLM call — returning canned reply")
    return {"messages": [AIMessage(content="哈囉！我是算術助理，有加法問題儘管問我。")]}


graph = StateGraph(GraphState)
graph.add_node("math_agent", math_agent)
graph.add_node("greeting_node", greeting_node)
graph.add_conditional_edges(
    START, router, {"greeting_node": "greeting_node", "math_agent": "math_agent"}
)
graph.add_edge("greeting_node", END)
graph.add_edge("math_agent", END)

app = graph.compile()


def main() -> None:
    for user_input in ["你好", "幫我算 12 加 30"]:
        print(f"\n=== 使用者: {user_input} ===")
        result = app.invoke({"messages": [{"role": "user", "content": user_input}]})
        print(f"Agent: {result['messages'][-1].content}")


if __name__ == "__main__":
    main()
