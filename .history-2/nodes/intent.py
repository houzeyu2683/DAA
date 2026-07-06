from typing import Literal, TypedDict
from langchain_core.messages import SystemMessage, AIMessage, filter_messages
# from pydantic import BaseModel
import json
from core import getModel
from core.status import State

model = getModel()

class Intent(TypedDict):
    type: Literal["chat", 'stats', "clarify"]
    stats: bool
    plot: bool

classifier = model.with_structured_output(Intent)
content = """
你是一個資料分析助理，負責判斷使用者意圖。

請根據聊天紀錄輸出一個結構化結果，包含三個欄位：

1. type
- chat：一般聊天、問候、知識問答，不需要執行資料分析。
- plan：需求已足夠明確，可以直接執行資料分析。
- clarify：需求不足，需要先詢問使用者。

2. stats
判斷使用者是否提到需要執行統計分析。
若有提到任何統計分析，回傳 true，否則 false。

統計分析包含但不限於：
- t-test
- ANOVA
- Mann-Whitney U test
- Kruskal-Wallis test
- Chi-square test
- Correlation
- Regression
- PCA
- Cluster analysis
- Descriptive statistics
- 平均、標準差、中位數、百分位數等統計摘要

3. plot
判斷使用者是否提到需要繪製圖表。
若有提到任何圖表或視覺化需求，回傳 true，否則 false。

圖表包含但不限於：
- box plot
- histogram
- scatter plot
- line chart
- bar chart
- violin plot
- heatmap
- pie chart
- ROC curve
- PCA plot
- 任何「畫圖」、「繪圖」、「視覺化」、「plot」、「chart」等描述

注意：
- stats 與 plot 可以同時為 true。
- stats、plot 與 type 是獨立判斷。
- 即使 type 為 clarify，只要使用者有提到統計分析或繪圖需求，仍須正確設定 stats 或 plot。

範例：

使用者：「你好」
→
{
  "type": "chat",
  "stats": false,
  "plot": false
}

使用者：「幫我分析」
→
{
  "type": "clarify",
  "stats": true,
  "plot": false
}

使用者：「幫我畫圖」
→
{
  "type": "clarify",
  "stats": false,
  "plot": true
}

使用者：「幫我畫 Equipment 和 包含CP_ 的 box plot」
→
{
  "type": "plan",
  "stats": false,
  "plot": true
}

使用者：「幫我對 Equipment 做 ANOVA」
→
{
  "type": "plan",
  "stats": true,
  "plot": false
}

使用者：「幫我對 Equipment 做 ANOVA，並畫 box plot」
→
{
  "type": "plan",
  "stats": true,
  "plot": true
}
"""

def intent_node(state: State) -> dict:
    conversation = [SystemMessage(content)] + state['messages']
    intent = classifier.invoke(conversation)
    messages = [AIMessage(json.dumps(intent, ensure_ascii=False))]
    return {"messages": messages, 'intent': intent}
