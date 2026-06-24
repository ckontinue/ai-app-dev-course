"""09c：加第三个工具 — 实时汇率查询（接真实 API）

新增工具 get_exchange_rate，调 frankfurter.app 免费 API
加一个新工具只需 3 步：①定义工具描述 ②写实现函数 ③注册到 TOOLS_MAP
"""

import anthropic, chromadb, json, requests

client = anthropic.Anthropic()

# ========== 1. 知识库（不动）==========
kc = chromadb.Client()
col = kc.create_collection("kb_v3")
with open("company_docs.txt", encoding="utf-8") as f:
    for i, c in enumerate(f.read().split("\n\n")):
        if c.strip():
            col.add(documents=[c.strip()], ids=[str(i)])

# ========== 2. 工具箱（现在有 3 把扳手）==========
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
    },
    # ── 新增工具 ──
    {
        "name": "get_exchange_rate",
        "description": "查询实时汇率，如人民币兑美元、日元兑人民币",
        "input_schema": {
            "type": "object",
            "properties": {
                "from_currency": {"type": "string", "description": "源货币代码，如 CNY USD JPY"},
                "to_currency": {"type": "string", "description": "目标货币代码，如 CNY USD JPY"}
            },
            "required": ["from_currency", "to_currency"]
        }
    }
]

# ========== 3. 工具实现 ==========
def search_knowledge_base(query):
    r = col.query(query_texts=[query], n_results=2)
    return {"results": r["documents"][0]}

def get_weather(city):
    try:
        resp = requests.get(f"https://wttr.in/{city}?format=%C+%t", timeout=5)
        return {"city": city, "weather": resp.text.strip()}
    except:
        return {"city": city, "weather": "查询失败"}

# ── 新增：调真实汇率 API ──
def get_exchange_rate(from_currency, to_currency):
    """调 frankfurter.app 获取实时汇率，免费无需 KEY"""
    try:
        url = f"https://api.frankfurter.app/latest?from={from_currency}&to={to_currency}"
        resp = requests.get(url, timeout=5)
        data = resp.json()
        rate = data["rates"][to_currency]
        return {
            "from": from_currency,
            "to": to_currency,
            "rate": rate,
            "date": data["date"]
        }
    except Exception as e:
        return {"error": str(e)}

TOOLS_MAP = {
    "search_knowledge_base": search_knowledge_base,
    "get_weather": get_weather,
    "get_exchange_rate": get_exchange_rate,  # ← 注册新工具
}

# ========== 4. 主循环（不改）==========
SYSTEM = "你是极光科技助手小光，热情口语。需要查公司资料、天气、汇率时调用对应工具。"

history = []
print("🤖 极光助手 3 工具版已上线（/quit 退出）")
print("   🛠 工具箱：查资料 / 查天气 / 查汇率\n")

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
            print(f"  🔧 [调用: {name}({args})]")
            result = TOOLS_MAP[name](**args)
            print(f"  📦 [结果: {json.dumps(result, ensure_ascii=False)[:80]}...]")

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
