from nodes.orchestration import OrchestrationState
from pathlib import Path
import os
from typing import Optional
import uuid
import duckdb as db
import pandas as pd
from dotenv import load_dotenv
from scipy import stats
from langchain_core.messages import SystemMessage, HumanMessage
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableConfig
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from MCP_server.client import fetch_tools
import asyncio
from string import Template


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


server_name = os.environ["MCP_CHART_SERVER_NAME"]
server_url = os.environ["MCP_CHART_SERVER_URL"]
server_port = os.environ["MCP_CHART_SERVER_PORT"]
port = int(server_port)
tools = asyncio.run(fetch_tools(server_name, server_url, port))


# @tool
# def read_statistic_table(database_path: str, statistic_table_name: str, top_number: int = 20) -> dict:
#     """查看統計結果表中差異最顯著的前 N 筆資料(所有統計工具都會依 p_value 
#     由小到大排序後保存到資料庫中(p_value 越小代表差異越顯著)。

#     參數:
#         database_path: DuckDB 資料庫檔案的路徑。
#         statistic_table_name: 統計結果表名稱(例如 anova_with_cats_and_nums 產生的表)。
#         top_number: 要取出的筆數，預設從差異最大開始取前 20 筆
#     """
#     con = db.connect(database_path, read_only=True)
#     try:
#         df = con.execute(
#             f"SELECT * FROM {statistic_table_name}"
#         ).df()
#     finally:
#         con.close()

#     if df.empty:
#         return f"表 {statistic_table_name} 沒有資料。"

#     df = df.head(top_number) if top_number >= 0 else df.tail(-top_number)

#     return {"overview": df.to_string()}


# @tool
# def plot_box_chart(
#     database_path: str, 
#     table_name: str, 
#     category_name: str, 
#     numeric_name: str, 
#     image_path: str
# ) -> str:
#     """對指定表裡的類別欄位(category_name)與數值欄位(numeric_name)畫箱型圖(box chart)，
#     圖片存成 PNG 檔案，回傳檔案路徑與簡短說明文字。

#     參數:
#         database_path: DuckDB 資料庫檔案的路徑。
#         table_name: 資料表名稱(需為含有逐筆資料的原始表，不能是統計結果表)。
#         category_name: 類別欄位名稱(分組依據，畫在 x 軸)。
#         numeric_name: 數值欄位名稱(要畫分布的對象，畫在 y 軸)。
#         image_path: 圖檔輸出路徑(建議放在 workspace 底下)。
#     """
#     con = db.connect(database_path, read_only=True)
#     try:
#         all_cols = [row[0] for row in con.execute(f"DESCRIBE {table_name}").fetchall()]
#         if category_name not in all_cols or numeric_name not in all_cols:
#             return f"欄位 {category_name} 或 {numeric_name} 不存在於表 {table_name} 中，未畫圖。"

#         df = con.execute(f"SELECT {category_name}, {numeric_name} FROM {table_name}").df()
#     finally:
#         con.close()

#     groups = {name: g[numeric_name].dropna() for name, g in df.groupby(category_name) if len(g) > 0}
#     if len(groups) < 2:
#         return f"欄位 {category_name} 的分組數量不足，未畫圖。"

#     try:
#         fig, ax = plt.subplots()
#         ax.boxplot(groups.values(), tick_labels=list(groups.keys()))
#         ax.set_xlabel(category_name)
#         ax.set_ylabel(numeric_name)
#         ax.set_title(f"{numeric_name} by {category_name}")
#         plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
#         fig.tight_layout()

#         save_path = os.path.abspath(image_path)
#         Path(save_path).parent.mkdir(parents=True, exist_ok=True)
#         fig.savefig(save_path)
#         plt.close(fig)

#     except Exception as e:
#         print(e)

#     return f"已將 {category_name} x {numeric_name} 的箱型圖存成圖檔，路徑：{save_path}"


# tools = [read_statistic_table, plot_box_chart]

CHART_SYSTEM_PROMPT = Template(
    # ── Role & Scope ──────────────────────────────
    "You are a data visualization analyst, responsible for interpreting "
    "statistical results and using visualization techniques to chart the "
    "raw data.\n"
    "Your job is to read the statistical data and create visualizations based "
    "on the user's question."
    "\n\n"
    # ── Workspace Path ────────────────────────────
    "Workspace path: $workspace\n"
    "All databases, statistical result tables, and chart outputs for this task "
    "must be placed under this workspace, unless the user explicitly specifies "
    "a different path."
    "\n\n"
    # ── Constraints ───────────────────────────────
    "You must never generate any code."
    "\n\n"
    # ── Reporting Format ──────────────────────────
    "When reporting on the task:\n"
    "- Briefly describe what you did\n"
    "- You must clearly state the location of the chart file(s)\n"
    "- Do not include unnecessary filler\n"
    "\n\n"
    # ── Output Language ───────────────────────────
    "IMPORTANT: Regardless of the language used in this system prompt, you "
    "must always respond to the user in Traditional Chinese (繁體中文)."
)

chart_agent = create_agent(
    model,
    tools=tools,
)

ATTEMPT = 3
async def chart_node(state: OrchestrationState, config: RunnableConfig) -> dict:
    # print("畫圖")
    workspace = config["configurable"]['workspace']
    chart_system_prompt = CHART_SYSTEM_PROMPT.substitute(workspace=workspace)
    messages = [SystemMessage(content=chart_system_prompt)] + state['messages']

    attempt = 0
    while attempt < ATTEMPT:
        try:
            response = await chart_agent.ainvoke({"messages": messages}, config={"max_concurrency": 1})
            break
        except Exception as e:
            print(e)
        attempt += 1
        continue

    assert attempt != 3, 'chart node 超過嘗試次數'

    # for message in response['messages']:
    #     message.pretty_print()

    # print("畫圖END")
    # content = response["messages"][-1].content
    # update = {"messages": [HumanMessage(content=content)]}

    response["messages"][-1].pretty_print()
    print("\n\n")
    update = {"messages": response["messages"][-1:]}
    return update
