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
from collections import Counter
import asyncio
from MCP_server.client import fetch_tools
from nodes.orchestration import OrchestrationState
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


server_name = os.environ["MCP_ANALYSIS_SERVER_NAME"]
server_url = os.environ["MCP_ANALYSIS_SERVER_URL"]
server_port = os.environ["MCP_ANALYSIS_SERVER_PORT"]
port = int(server_port)
tools = asyncio.run(fetch_tools(server_name, server_url, port))


# def _resolve_cols(names: list, pattern: dict, all_cols: list) -> list:
#     if names:
#         return [c for c in names if c in all_cols]
#     matched = []
#     for p, mode in (pattern or {}).items():
#         if mode == "contains":
#             matched += [c for c in all_cols if p in c]
#         elif mode == "startwith":
#             matched += [c for c in all_cols if c.startswith(p)]
#         elif mode == "endwith":
#             matched += [c for c in all_cols if c.endswith(p)]
#     return [c for i, c in enumerate(matched) if c not in matched[:i]]


# def _resolve_tag(names: list, pattern: dict) -> str:
#     if names:
#         return '_'.join(names)
#     return "_".join([k for k in (pattern or {})])


# def _create_table(
#     database_path: str, table_name: str, table_content: pd.DataFrame
# ) -> bool:

#     con = db.connect(database_path)
#     con.register("table_content", table_content)
#     con.execute(
#         f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM table_content"
#     )
#     con.close()
#     return True


# @tool
# def get_table_shape(database_path: str, table_name: str) -> list:
#     """獲得資料表的資料數與欄位數，回傳 [row_count, col_count]。

#     參數:
#         database_path: DuckDB 資料庫檔案的路徑。
#         table_name: 要查詢的資料表名稱。
#     """
#     con = db.connect(database_path, read_only=True)
#     try:
#         row_count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
#         col_count = len(con.execute(f"DESCRIBE {table_name}").fetchall())
#     finally:
#         con.close()
#     return [row_count, col_count]

# @tool
# def get_columns_type(database_path: str, table_name: str, columns_name: list) -> dict:
#     """查詢資料表中指定欄位的型別。

#     輸出格式範例: {"col_1": "BIGINT", "col_2": "VARCHAR", ....}

#     參數:
#         database_path: DuckDB 資料庫檔案的路徑。
#         table_name: 要查詢的資料表名稱。
#         columns_name: 要查詢型別的欄位名稱清單。
#     """
#     con = db.connect(database_path, read_only=True)
#     try:
#         schema = con.execute(f"DESCRIBE {table_name}").fetchall()
#     finally:
#         con.close()
#     types_by_col = {row[0]: row[1] for row in schema}
#     return {col: types_by_col[col] for col in columns_name if col in types_by_col}

# @tool
# def get_columns_type_distribution(database_path: str, table_name: str, columns_pattern: dict) -> dict:
#     """依欄位名稱比對規則，統計符合條件的欄位中各種型別各有幾個。

#     columns_pattern 格式是 {pattern字串: 比對方式}，例如:
#         - {"XXXX": "contains"}   欄位名稱包含 "XXXX"
#         - {"XXXX": "startwith"}  欄位名稱開頭是 "XXXX"
#         - {"XXXX": "endwith"}    欄位名稱結尾是 "XXXX"

#     輸出格式範例: {"BIGINT": 22, "VARCHAR": 123, ....}

#     參數:
#         database_path: DuckDB 資料庫檔案的路徑。
#         table_name: 要查詢的資料表名稱。
#         columns_pattern: 欄位名稱的比對規則。
#     """
#     con = db.connect(database_path, read_only=True)
#     try:
#         schema = con.execute(f"DESCRIBE {table_name}").fetchall()
#     finally:
#         con.close()

#     matched_types = []
#     for row in schema:
#         col_name, col_type = row[0], row[1]
#         for pattern, mode in columns_pattern.items():
#             if mode == "contains" and pattern in col_name:
#                 matched_types.append(col_type)
#                 break
#             if mode == "startwith" and col_name.startswith(pattern):
#                 matched_types.append(col_type)
#                 break
#             if mode == "endwith" and col_name.endswith(pattern):
#                 matched_types.append(col_type)
#                 break

#     return dict(Counter(matched_types))

# @tool
# def preview_columns(database_path: str, table_name: str) -> str:
#     """列出資料表的所有欄位名稱，串成一個字串。

#     若欄位數量小於等於 12 個，直接用逗號串接全部欄位；
#     若超過 12 個，只顯示前 3 個與後 3 個欄位名稱，中間用 '......' 省略。

#     參數:
#         database_path: DuckDB 資料庫檔案的路徑。
#         table_name: 要查詢的資料表名稱。
#     """
#     con = db.connect(database_path, read_only=True)
#     try:
#         columns = [row[0] for row in con.execute(f"DESCRIBE {table_name}").fetchall()]
#     finally:
#         con.close()

#     if len(columns) <= 12:
#         return ','.join(columns)
#     return ','.join(columns[:3]) + '......' + ','.join(columns[-3:])


# @tool
# def difference_analysis(
#     database_path: str,
#     table_name: str,
#     stats_table_name: str, 
#     categories: Optional[list] = None,
#     categories_pattern: Optional[dict] = None,
#     numerics: Optional[list] = None,
#     numerics_pattern: Optional[dict] = None,
#     # stats_metric: str = 'p_value',
#     top_number: int = 20
# ) -> dict:
#     """對類別欄位與數值欄位做單因子 ANOVA。
#     categories/numerics 各自可以是一個或多個欄位，用 list 明確列出欄位名稱。

#     在比對之前，你需要去檢查欄位的類型

#     如果欄位數量很多、無法一一列舉(例如所有包含某個字串的欄位)，
#     改用 categories_pattern/numerics_pattern 比對欄位名稱，格式是 {pattern字串: 比對方式}，
#     比對方式可以是 "contains"(包含)、"startwith"(開頭是)、"endwith"(結尾是)。

#     categories 與 categories_pattern 必須只能擇一輸入；
#     numerics 與 numerics_pattern 必須只能擇一輸入。

#     內部會對「類別欄位 x 數值欄位」的每一種組合各跑一次 ANOVA，
#     完整結果存入資料庫的一張新表，回傳依 p_value 排序後的截斷預覽文字。

#     參數:
#         database_path: DuckDB 資料庫檔案的路徑。
#         table_name: 要分析的資料表名稱。
#         categories: 類別欄位名稱清單。
#         categories_pattern: 類別欄位的比對規則。
#         numerics: 數值欄位名稱清單。
#         numerics_pattern: 數值欄位的比對規則。
#         top_number: 如果有指定想要看前幾個結果，可以用這個設定，預設是前20個
#     """
#     print("difference_analysis")
#     con = db.connect(database_path, read_only=True)
#     try:
#         all_cols = [row[0] for row in con.execute(f"DESCRIBE {table_name}").fetchall()]

#         cat_cols = _resolve_cols(categories, categories_pattern, all_cols)
#         num_cols = _resolve_cols(numerics, numerics_pattern, all_cols)

#         results = []
#         for cat in cat_cols:
#             for num in num_cols:
#                 df = con.execute(f"SELECT {cat}, {num} FROM {table_name}").df()
#                 groups = [g[num].dropna() for _, g in df.groupby(cat) if len(g) > 0]
#                 if len(groups) < 2:
#                     continue
#                 f_stat, p_value = stats.f_oneway(*groups)
#                 results.append({
#                     "table_name": table_name,
#                     "cat": cat,
#                     "num": num,
#                     "n_groups": len(groups),
#                     "f_stat": f_stat,
#                     "p_value": p_value,
#                 })
#     finally:
#         con.close()

#     if not results:
#         # print(cat, num) 
#         return "沒有找到符合條件的類別欄位與數值欄位組合，未執行任何 ANOVA。"

#     stats_metric = 'p_value'
#     results_df = pd.DataFrame(results).sort_values(stats_metric)
#     # print(results_df)
    
#     stats_table_name = stats_table_name + '_' + uuid.uuid4().hex[:4]

#     _create_table(database_path, stats_table_name, results_df)

#     top_rows = results_df.head(top_number)
#     top_summary = "\n".join(
#         f"{i+1}. {row['cat']} x {row['num']}（{stats_metric}={row[stats_metric]:.4e}）"
#         for i, row in enumerate(top_rows.to_dict("records"))
#     )
#     conclusion = f"依照 {stats_metric} 排序，差異最顯著的前 {top_number} 個組合：\n{top_summary}"
#     # print(conclusion)

#     preview = results_df.to_string(max_rows=20, show_dimensions=False)
#     return {
#         "stats_table_name": {
#             stats_table_name: "統計結果存放在此。"
#         },
#         "stats_table_preview": preview,        # 且 preview 本身已經拿掉 f_stat
#         "stats_metric": {
#             stats_metric: "分析主要依據的指標。"
#         },     # 明確標註判斷依據
#         "conclusion": conclusion
#     }


# tools = [
#     difference_analysis, get_table_shape, get_columns_type, 
#     get_columns_type_distribution, preview_columns
# ]

ANALYSIS_SYSTEM_PROMPT = Template(
    # ── Role & Scope ──────────────────────────────
    "You are a statistical analysis expert. Your job is to answer "
    "data-statistics questions about tables that already exist in the DuckDB database.\n"
    "You may only query the raw data in read-only mode. You must never insert, "
    "modify, or delete any data in the original tables.\n"
    "You must not generate any code.\n"
    "Before analyzing a variable, you must first check its data type, "
    "then pass the correct parameters accordingly.\n"
    "Your responsibility is limited to statistical analysis only. Data loading and "
    "visualization/charting are the responsibility of other experts. "
    "You must not attempt to perform any task outside of statistical analysis "
    "(e.g. creating charts), even if the user's request also mentions charting or "
    "other needs — only complete the statistical analysis part and leave the rest "
    "to the downstream workflow. Do not attempt it yourself."
    "\n\n"

    # ── Workspace Path ────────────────────────────
    "Workspace path: $workspace\n"
    "All databases, statistical result tables, and chart outputs for this task "
    "must be placed under this workspace, unless the user explicitly specifies "
    "a different path."
    "\n\n"

    # ── Execution Rules ───────────────────────────
    "Before you call a tool and receive its actual returned result, you must never "
    "write any content that looks like statistical numbers, tables, or analysis "
    "conclusions (never fabricate numbers). You may only describe results based on "
    "what the tool actually returns.\n"
    "After completing the task, summarize what you did and list the key information "
    "(e.g. the name of the resulting statistics table)."
    "\n\n"

    # ── Metric Rules (extend this list when adding new methods) ──
    "Each statistical method may have multiple reference metrics, but you must "
    "strictly follow this rule for the final analysis basis:\n"
    "- For difference_analysis, use p_value as the sole metric."
    "\n\n"

    # ── Output Language ───────────────────────────
    # "IMPORTANT: Regardless of the language used in this system prompt, you must "
    # "always respond to the user in Traditional Chinese (繁體中文)."
    # "\n\n"

    # ── Tone ──────────────────────────────────────
    "Do not include unnecessary filler. Be concise."
)
analysis_agent = create_agent(
    model,
    tools=tools,
    # system_prompt=ANALYSIS_NODE_PROMPT,
)


async def analysis_node(state: OrchestrationState, config: RunnableConfig) -> dict:
    # print(" 開始 ana node")
    workspace = config["configurable"]['workspace']
    analysis_system_prompt = ANALYSIS_SYSTEM_PROMPT.substitute(workspace=workspace)
    messages = [SystemMessage(content=analysis_system_prompt)] + state['messages']#[-1:]

    # import time
    # a = time.perf_counter()
    response = await analysis_agent.ainvoke({"messages": messages}, config={"max_concurrency": 1})
    # b = a - time.perf_counter()
    # print("cost----------------- ", b)
    # for message in response['messages']:
    #     message.pretty_print()


    # print(" 結束 ana node ")
    response["messages"][-1].pretty_print()
    print("\n\n")
    # content = response["messages"][-1].content
    # update = {"messages": [HumanMessage(content=content)]}
    update = {"messages": response["messages"][-1:]}
    return update
