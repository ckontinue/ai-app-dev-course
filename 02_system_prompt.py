"""第二课：system prompt — 给 AI 设定身份"""

import anthropic

client = anthropic.Anthropic()
question = "退货流程是什么"

# ---- 示例 1: 没有 system prompt（裸问） ----
print("=" * 50)
print("【裸问，没有 system prompt】")
print("=" * 50)
r = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=100, thinking={"type": "disabled"},
    messages=[{"role": "user", "content": question}]
)
for b in r.content:
    if b.type == "text":
        print(b.text)

# ---- 示例 2: 设定角色 — 客服 ----
print("\n" + "=" * 50)
print("【system: 你是淘宝客服，态度热情，用口语】")
print("=" * 50)
r = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=100, thinking={"type": "disabled"},
    system="你是淘宝客服，态度热情，用口语回话，结尾加个亲。",  # ← system prompt
    messages=[{"role": "user", "content": question}]
)
for b in r.content:
    if b.type == "text":
        print(b.text)

# ---- 示例 3: 设定角色 — 严肃律师 ----
print("\n" + "=" * 50)
print("【system: 你是律师，专业严谨，用书面语】")
print("=" * 50)
r = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=100, thinking={"type": "disabled"},
    system="你是电商法专业律师，用严谨的书面语回复，分条列举法律依据。",
    messages=[{"role": "user", "content": question}]
)
for b in r.content:
    if b.type == "text":
        print(b.text)
