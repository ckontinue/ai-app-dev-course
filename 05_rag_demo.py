"""第五课：RAG — 让 AI 读你的内部文件再回答"""

import anthropic

client = anthropic.Anthropic()

# 1. 读文件 → 切成块
with open("company_docs.txt", encoding="utf-8") as f:
    raw = f.read()

chunks = [c.strip() for c in raw.split("\n\n") if c.strip()]  # 按空行切开

# 2. 模拟"检索"：根据关键词打分，找最相关的块
def search(query, chunks, top_n=2):
    scored = []
    for c in chunks:
        score = sum(1 for word in query if word in c)  # 命中几个关键词
        scored.append((score, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:top_n]]

# 3. 提问
while True:
    q = input("\n你：")
    if q == "/quit":
        break

    # 检索
    hits = search(q, chunks)
    context = "\n\n".join(hits)

    # 喂给模型
    r = client.messages.create(
        model="claude-sonnet-4-6", max_tokens=200, thinking={"type": "disabled"},
        system=f"你根据以下内部文档回答用户问题。文档中没有的信息就说不知道。\n\n【内部文档】\n{context}",
        messages=[{"role": "user", "content": q}]
    )
    for b in r.content:
        if b.type == "text":
            print(f"AI：{b.text}")
