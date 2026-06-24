"""第一课：调用 Claude API，实现最简单的一次对话"""

import anthropic
import os

# 1. 创建客户端 — 自动读取环境变量 ANTHROPIC_API_KEY
client = anthropic.Anthropic()

# 2. 发送请求
response = client.messages.create(
    model="claude-sonnet-4-6",       # 选模型：性价比之王
    max_tokens=200,                  # 回复最长 200 tokens（≈300 字）
    thinking={"type": "disabled"},   # 关闭思考模式，只要最终回复
    messages=[
        {"role": "user", "content": "用一句话介绍什么是 RAG"}
    ]
)

# 3. 取出回复内容（过滤掉 thinking 块，只要文本）
print("🤖 Claude 回复：")
for block in response.content:
    if block.type == "text":
        print(block.text)

# 4. 看看花了多少 token（花了多少钱）
print(f"\n💰 消耗: 输入 {response.usage.input_tokens} tokens, 输出 {response.usage.output_tokens} tokens")
