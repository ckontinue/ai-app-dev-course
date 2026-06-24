"""第九课：RAG + Agent 合体 — 有知识库又能动手的全能助手"""

import anthropic, chromadb, json

client = anthropic.Anthropic()

# ========== 1. 知识库（向量检索）==========
kc = chromadb.Client()
col = kc.create_collection("knowledge_base")
with open("company_docs.txt", encoding="utf-8") as f:
    for i, c in enumerate(f.read().split("\n\n")):
        if c.strip():
            col.add(documents=[c.strip()], ids=[str(i)])

# ========== 2. 工具箱 ==========
tools = [
    {
        "name": "search_knowledge_base",
        "description": "搜索公司内部知识库",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "搜索词"}},
            "required": ["query"]
        }
    },
    {
        "name": "get_weather",
        "description": "获取实时天气",
        "input_schema": {
            "type": "object",
            "properties": {"city": {"type": "string", "description": "城市名"}},
            "required": ["city"]
        }
    }
]

def search_knowledge_base(query):
    r = col.query(query_texts=[query], n_results=2)
    return {"results": r["documents"][0]}

def get_weather(city):
    return {"city": city, "天气": "晴天", "温度": 28}

TOOLS_MAP = {"search_knowledge_base": search_knowledge_base, "get_weather": get_weather}

# ========== 3. 主循环 ==========
SYSTEM = "你是极光科技助手小光，热情口语。需要查公司资料或实时数据时调用工具。"

history = []
print("🤖 极光助手已上线（/quit 退出）\n")

while True:
    user = input("你：")
    if user == "/quit":
        break

    history.append({"role": "user", "content": user})

    r = client.messages.create(
        model="claude-sonnet-4-6", max_tokens=400, thinking={"type": "disabled"},
        system=SYSTEM, tools=tools, messages=history
    )

    reply = ""
    for block in r.content:
        if block.type == "text":
            reply = block.text
        elif block.type == "tool_use":
            name, args = block.name, block.input
            print(f"  [调用: {name}({args})]")
            result = TOOLS_MAP[name](**args)

            history.append({"role": "assistant", "content": [block]})
            history.append({"role": "user", "content": [{
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result, ensure_ascii=False)
            }]})

            r2 = client.messages.create(
                model="claude-sonnet-4-6", max_tokens=400, thinking={"type": "disabled"},
                system=SYSTEM, tools=tools, messages=history
            )
            for b2 in r2.content:
                if b2.type == "text":
                    reply = b2.text
                    history.append({"role": "assistant", "content": b2.text})

    if reply:
        print(f"小光：{reply}\n")
