import os

import dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

# tools/system.py 裡目前有 11 個函式，這裡先全部 import 進來，
# 但下面 create_agent 的 tools=[...] 目前只實際接了 list_file_names、
# list_folder_names 這兩個 —— 照之前的習慣，工具是一個一個接、驗證過再加下一個，
# 所以這裡先把名字都匯入備用，其餘的還沒真的讓 agent 能呼叫。
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


# 讀取專案根目錄的 .env 檔案，把裡面的 MODEL_NAME / MODEL_URL / MODEL_KEY
# 等變數載入到 os.environ，下面才能用 os.environ[...] 取得。
dotenv.load_dotenv()

# model、workflow 都是模組層級變數：這支檔案第一次被 import 時就會建立好，
# 之後不管誰 import workflow 這個模組，拿到的都是同一個 model / workflow 物件，
# 不會每次都重新初始化模型、重新接工具。
# ChatOpenAI 這裡雖然叫 OpenAI，但只要目標服務相容 OpenAI 的 API 格式，
# 換成 base_url 指向別的服務（例如這裡用的 OpenRouter）一樣能用。
model = ChatOpenAI(
    model=os.environ["MODEL_NAME"],
    base_url=os.environ["MODEL_URL"],
    api_key=os.environ["MODEL_KEY"],
    temperature=0,  # 0 代表盡量穩定、少隨機發揮，適合需要精準操作工具的助理。
)

# create_agent 會把 model、tools、checkpointer、middleware 組成一個
# 完整的 LangGraph agent（背後其實是一張圖，但這裡不用自己畫圖）。
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
]
workflow = create_agent(
    model,
    # tools 是 agent 目前真正能呼叫的函式清單，來自 tools/system.py。
    # 直接把函式本身丟進來即可，create_agent 會自動讀函式的參數型別、
    # 回傳型別跟 docstring，轉換成模型看得懂的工具描述。
    tools=tools,
    # checkpointer 負責把每一輪對話的狀態（訊息、工具呼叫紀錄）存起來，
    # 之後同一個 thread_id 再呼叫時才能接續之前的對話。
    # InMemorySaver 是存在記憶體裡，process 重啟就會消失，
    # 之後如果要跨重啟保留，才需要換成會寫進硬碟或資料庫的 checkpointer。
    checkpointer=InMemorySaver(),
    # middleware 是掛在 agent 執行流程前後的攔截器，可以在模型被呼叫前後
    # 動一些手腳。這裡用 SummarizationMiddleware 解決「對話太長」的問題：
    middleware=[
        SummarizationMiddleware(
            model=model,
            # trigger：什麼時候要觸發「壓縮舊對話」。
            # ("tokens", 4000) 代表累積的訊息 token 數到達 4000 就觸發。
            # 之所以不用 ("fraction", 0.8) 這種「佔模型上限的比例」寫法，
            # 是因為這需要 langchain 知道這個模型的最大輸入 token 數，
            # 但目前用的是 langchain 不認識的自訂模型（OpenRouter 上的模型），
            # 沒有登記過上限資訊，用 fraction 在建立時就會直接報錯。
            trigger=("tokens", 4000),
            # keep：觸發壓縮後，要保留「最近」多少內容不被摘要掉。
            # ("messages", 20) 代表壓縮完，最近 20 則訊息維持原樣，
            # 更早的訊息會被濃縮成一段摘要塞回對話裡，讓 agent 還記得重點，
            # 但不用把所有原始內容都留著占用 context。
            keep=("messages", 20),
        ),
    ],
)
