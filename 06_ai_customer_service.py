"""第六课：完整 AI 智能客服 = 人格 + 知识库 + 记忆"""

import anthropic

client = anthropic.Anthropic()

# ---- 读知识库 ----
with open("company_docs.txt", encoding="utf-8") as f:
    chunks = [c.strip() for c in f.read().split("\n\n") if c.strip()]

# ---- 人格 ----
PERSONA = "你是极光科技客服小光，热情专业，用口语回复，结尾加「~」符号。"

def search(query, chunks, top_n=2):
    """关键词检索"""
    scored = [(sum(1 for w in query if w in c), c) for c in chunks]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:top_n] if _ > 0]  # 至少命中1个词

# ---- 主程序 ----
history = [{"role": "user", "content": "你好"}]

print("👩‍💼 极光科技智能客服已上线（/quit 退出）\n")
while True:
    user = input("你：")
    if user == "/quit":
        print("小光：再见，有需要随时找我~")
        break

    # 检索
    hits = search(user, chunks)
    context = "\n\n".join(hits) if hits else ""

    # 拼 system：人格 + 知识库
    system = PERSONA
    if context:
        system += f"\n\n参考以下内部文档回答，没有的信息就说不知道：\n{context}"

    history.append({"role": "user", "content": user})

    r = client.messages.create(
        model="claude-sonnet-4-6", max_tokens=200, thinking={"type": "disabled"},
        system=system,
        messages=history
    )

    reply = None
    for b in r.content:
        if b.type == "text":
            reply = b.text

    print(f"小光：{reply}\n")
    history.append({"role": "assistant", "content": reply})
