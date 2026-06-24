"""第三课：多轮对话 — AI 记住上下文靠的是把历史全发回去"""

import anthropic

client = anthropic.Anthropic()

# ---- 示例 1: 不传历史，AI 没有记忆 ----
print("=" * 50)
print("【没有记忆】每次只发当前问题")
print("=" * 50)

# 第一轮
r = client.messages.create(
    model="claude-sonnet-4-6", max_tokens=80, thinking={"type": "disabled"},
    messages=[{"role": "user", "content": "我叫梁利军，记好了。"}]
)
for b in r.content:
    if b.type == "text": print(b.text)

# 第二轮：假装接着问，但没传历史
r = client.messages.create(
    model="claude-sonnet-4-6", max_tokens=80, thinking={"type": "disabled"},
    messages=[{"role": "user", "content": "我叫什么名字？"}]
)
for b in r.content:
    if b.type == "text": print("\n>>> " + b.text)


# ---- 示例 2: 手动传历史，AI 就有记忆了 ----
print("\n" + "=" * 50)
print("【有记忆】把历史对话也塞进 messages")
print("=" * 50)

history = []  # 记在这里

# 第一轮
history.append({"role": "user", "content": "我叫梁利军，记好了。"})
r = client.messages.create(
    model="claude-sonnet-4-6", max_tokens=80, thinking={"type": "disabled"},
    system="用中文简短回复。",
    messages=history
)
reply = None
for b in r.content:
    if b.type == "text":
        reply = b.text
        print(b.text)
history.append({"role": "assistant", "content": reply})  # 把 AI 回复也记下来

# 第二轮：带着完整历史
history.append({"role": "user", "content": "我叫什么名字？"})
r = client.messages.create(
    model="claude-sonnet-4-6", max_tokens=80, thinking={"type": "disabled"},
    system="用中文简短回复。",
    messages=history
)
for b in r.content:
    if b.type == "text":
        print("\n>>> " + b.text)
