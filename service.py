import os
import dotenv
from agent.session import Session
from agent.agent import run_agent

_ = dotenv.load_dotenv()

DB_PATH = os.getenv("DB_PATH", ".data/workspace.db")

if __name__ == "__main__":
    session = Session(db_path=DB_PATH)
    print(f"DAA 啟動，連接資料庫：{DB_PATH}")
    print("輸入 'exit' 離開，'reset' 重置 session\n")

    while True:
        try:
            user_input = input("你：").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user_input:
            continue
        if user_input.lower() == "exit":
            break
        if user_input.lower() == "reset":
            session = Session(db_path=DB_PATH)
            print("[Session 已重置]\n")
            continue
        run_agent(session, user_input)
