import os
from typing import Optional
import uuid
import duckdb as db
import pandas as pd
from dotenv import load_dotenv
from scipy import stats
from langchain_core.messages import SystemMessage, HumanMessage
from langchain.agents import create_agent
from langgraph.graph import END
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableConfig
from string import Template
from nodes.orchestration import OrchestrationState

load_dotenv()
model_name = os.environ["MODEL_NAME"]
model_url = os.environ["MODEL_URL"]
model_key = os.environ["MODEL_KEY"]
model = ChatOpenAI(
    model=model_name,
    temperature=0,
    base_url=model_url,
    api_key=model_key,
)


SUMMARY_SYSTEM_PROMPT = (
    # ── Role & Scope ──────────────────────────────
    "You are a data analysis interpretation expert, responsible for responding "
    "to the user's original question at the end of the entire data analysis "
    "workflow.\n"
    "The priority order is as follows:\n"
    "\n\n"
    # ── Priority 1: Directly Answer the Question ──
    "1. Most importantly, directly answer the question the user originally "
    "asked.\n"
    "If the conversation history already contains actual statistical figures "
    "(e.g. p_value, f_stat), you must state the conclusion in plain language "
    "(e.g. whether there is a significant difference between the two groups). "
    "Do not merely report process-oriented statements such as \"analysis "
    "completed\" without stating the conclusion. "
    "Conclusions must always be based on the actual numbers returned by the "
    "tools; do not fabricate numbers yourself.\n"
    "\n\n"
    # ── Method-to-Metric Reference ─────────────────
    "When interpreting statistical results, you must draw conclusions based "
    "on the correct metric corresponding to the statistical method used; "
    "metrics must not be mixed up or misapplied. The mapping rules for this "
    "task are as follows:\n"
    "$method_metric_mapping\n"
    "If the conversation history does not clearly indicate which method was "
    "used, you must not assume the method type yourself; instead, determine "
    "the correct metric based on the actual field names returned by the "
    "tools.\n"
    "\n\n"
    # ── Priority 2: Supplement Key Information ─────
    "2. Next in priority is supplementing key information (e.g. database "
    "path, table name, statistical result table name, chart file path).\n"
    "\n\n"
    # ── Priority 3: Do Not Ask Unrequested Questions
    "3. Do not ask the user about next steps they have not requested (e.g. "
    "if the user did not ask for a chart, do not proactively ask whether "
    "they want one).\n"
    "\n\n"
    # ── Constraints & Format ────────────────────────
    "4. The response must cover every step that was executed in the past; "
    "avoid unnecessary filler.\n"
    "5. You must never generate any code.\n"
    "\n\n"
    # ── Output Language ─────────────────────────────
    "IMPORTANT: Regardless of the language used in this system prompt, you "
    "must always respond to the user in Traditional Chinese (繁體中文)."
)
summary_agent = create_agent(model)

# def _ensure_system_prompt(messages: list, prompt: str) -> list:
#     if messages and getattr(messages[0], "type", None) == "system":
#         return messages
#     return [{"role": "system", "content": prompt}] + list(messages)


def summary_node(state: OrchestrationState) -> dict:
    """整合對話紀錄，產生最終總結訊息。"""
    messages = [SystemMessage(SUMMARY_SYSTEM_PROMPT)] + state["messages"]
    # messages = _ensure_system_prompt(state["messages"], SUMMARY_PROMPT)
    response = summary_agent.invoke({"messages": messages})

    # for message in response['messages']:
    #     message.pretty_print()


    update = {"messages": response["messages"][-1:]}
    return update
