from workflow import agent

# 假設使用者已登入分析助理系統,對應到 .data/G72602/0e15/database.db
# 這個既有的資料庫(先固定寫死,之後再決定怎麼流進 State/config)
user_id = "G72602"
thread_id = "0e15"
database_path = f".data/data.db"
table_names = [
    "fifa_world_cup_2026_player_performance"
]

config = {
    "configurable": {
        "thread_id": thread_id,
        "database_path": database_path,
        "table_names": table_names,
    }
}

# {"messages": [{"role": "user", "content": "測試訊息"}]},
# {"messages": [{"role": "user", "content": "你好"}]},
# {"messages": [{"role": "user", "content": "幫我看一下球員進球數的趨勢"}]},
# {"messages": [{"role": "user", "content": "幫我算一下每個球員進球數的平均值跟標準差"}]},
# {"messages": [{"role": "user", "content": "幫我分析一下球員的進球表現,畫張圖,最後給我一份報告"}]},
# {"messages": [{"role": "user", "content": "這個資料集裡有多少筆資料"}]},
# {"messages": [{"role": "user", "content": "今天天氣真好，這個資料集裡有多少筆資料？我想對 age 欄位跟 weight_kg 進行相似度分析"}]},
# {"messages": [{"role": "user", "content": "我要看進球數跟所有防守相關欄位的相似度分析"}]},
# {"messages": [{"role": "user", "content": "我想知道助攻數與傳球相關欄位之間的相似度"}]},
# {"messages": [{"role": "user", "content": "我想知道影響出賽時間的所有體能相關欄位的相似度分析"}]},
# {"messages": [{"role": "user", "content": "我想了解影響進球數的所有技術面欄位的相似度分析"}]},

for update in agent.stream(
    # {"messages": [{"role": "user", "content": ""}]},
    # {"messages": [{"role": "user", "content": "資料庫有哪些表"}]},    
    {"messages": [{"role": "user", "content": "今天天氣真好，這個資料集裡有多少筆資料？我想對 age 欄位跟 weight_kg 進行相似度分析"}]},
    config=config,
    stream_mode="updates",
):
    print(update)
