"""第九课 B 版：RAG + Agent — 换 DeepSeek API"""

from openai import OpenAI
import chromadb, json, os

client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN", ""),
    base_url="https://api.deepseek.com"
)

# ========== 1. 知识库（不变）==========
kc = chromadb.Client()
col = kc.create_collection("kb_deepseek")
with open("company_docs.txt", encoding="utf-8") as f:
    for i, c in enumerate(f.read().split("\n\n")):
        if c.strip():
            col.add(documents=[c.strip()], ids=[str(i)])

# ========== 2. 工具箱（格式变了）==========
tools = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "搜索公司内部知识库",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "搜索词"}},
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取实时天气",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string", "description": "城市名"}},
                "required": ["city"]
            }
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
SYSTEM = {"role": "system", "content": "你是极光科技助手小光，热情口语。需要资料或实时数据时调用工具。"}

history = [SYSTEM]  # DeepSeek: system 直接放 messages 里
print("🤖 极光助手 DeepSeek 版已上线（/quit 退出）\n")

while True:
    user = input("你：")
    if user == "/quit":
        break

    history.append({"role": "user", "content": user})

    r = client.chat.completions.create(
        model="deepseek-chat",
        messages=history,
        tools=tools
    )

    msg = r.choices[0].message
    reply = ""

    if msg.content:
        reply = msg.content

    if msg.tool_calls:
        for tc in msg.tool_calls:
            name = tc.function.name
            args = json.loads(tc.function.arguments)
            print(f"  [调用: {name}({args})]")

            result = TOOLS_MAP[name](**args)

            # DeepSeek: tool 结果格式不同
            history.append(msg.model_dump())
            history.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result, ensure_ascii=False)
            })

        # 二次请求
        r2 = client.chat.completions.create(
            model="deepseek-chat",
            messages=history,
            tools=tools
        )
        reply = r2.choices[0].message.content
        history.append({"role": "assistant", "content": reply})

    if reply:
        print(f"小光：{reply}\n")
