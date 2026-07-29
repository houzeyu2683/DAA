import os
import sys
import gradio as gr

# 將專案根目錄加入 sys.path，以便 import main_reAct
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    # 假設您之後會將 main_reAct.py 封裝成一個可以被呼叫的函數
    # 這裡我們先模擬一個簡單的邏輯，實際使用時請確保 main_reAct 有對應的 entry point
    from main_reAct import agent, config
except ImportError:
    print("Error: Could not import main_reAct. Please ensure main_reAct.py is in the root directory and properly structured.")
    agent = None
    config = None

def run_agent_step(user_input, history):
    """
    處理 Agent 的對話邏輯
    """
    if agent is None:
        return history + [["System", "Error: Agent not initialized. Check main_reAct.py"]], "Error", "Error"

    # 模擬 Agent 執行 (實際應使用 agent.invoke)
    # 這裡為了讓 UI 能跑起來，我們先用 dummy 邏輯，您之後要換成真正的 agent.invoke
    try:
        # 實際執行
        from langchain_core.messages import HumanMessage
        response = agent.invoke(
            {"messages": [HumanMessage(content=user_input)]},
            config=config
        )
        
        # 取得最後一則訊息作為回應
        last_message = response["messages"][-1].content
        
        # 更新對話歷史
        history.append((user_input, last_message))
        
        # 這裡可以根據 Agent 的回傳內容，進一步解析出檔案列表或內容
        # 暫時回傳 dummy 資訊
        return history, "Files updated", "Content preview..."
    
    except Exception as e:
        history.append((user_input, f"Error: {str(e)}"))
        return history, "Error", str(e)

def update_file_list():
    """
    模擬獲取檔案列表
    """
    # 實際應呼叫 tools.system.list_files
    files = os.listdir('.')
    file_html = "<ul>" + "".join([f"<li>{f}</li>" for f in files]) + "</ul>"
    return file_html

with gr.Blocks(title="AI Agent File Manager") as demo:
    gr.Markdown("# 🤖 AI Agent File System Manager")
    
    with gr.Row():
        # 左側：聊天視窗
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(label="Agent Conversation", height=500)
            with gr.Row():
                msg = gr.Textbox(
                    show_label=False,
                    placeholder="輸入指令 (例如: '列出檔案', '讀取 README.md')",
                    scale=4
                )
                submit_btn = gr.Button("Send", variant="primary", scale=1)
            
            clear = gr.ClearButton([msg, chatbot])

        # 右側：檔案瀏覽與預覽
        with gr.Column(scale=2):
            with gr.Group():
                gr.Markdown("### 📂 File Explorer")
                file_tree = gr.HTML(value="<ul><li>Loading...</li></ul>")
                refresh_btn = gr.Button("🔄 Refresh Files", size="sm")
            
            with gr.Group():
                gr.Markdown("### 📄 Content Preview")
                file_preview = gr.Code(label="File Content", language="python", interactive=False)
                image_preview = gr.Image(label="Image Preview", visible=False)
                status_msg = gr.Textbox(label="Status", interactive=False)

    # 事件綁定
    def respond(message, chat_history):
        new_history, status, preview = run_agent_step(message, chat_history)
        # 這裡可以根據需要更新 file_tree
        return new_history, status, preview

    submit_btn.click(respond, [msg, chatbot], [chatbot, status_msg, file_preview])
    msg.submit(respond, [msg, chatbot], [chatbot, status_msg, file_preview])
    
    refresh_btn.click(update_file_list, None, file_tree)
    
    # 初始化載入檔案列表
    demo.load(update_file_list, None, file_tree)

if __name__ == "__main__":
    demo.launch()
