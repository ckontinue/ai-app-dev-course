"""第十课：部署 — 把 AI 助手做成网页"""

import anthropic, chromadb, json, gradio as gr, requests

# ---- 知识库 ----
kc = chromadb.Client()
col = kc.create_collection("knowledge_base")
with open("company_docs.txt", encoding="utf-8") as f:
    for i, c in enumerate(f.read().split("\n\n")):
        if c.strip():
            col.add(documents=[c.strip()], ids=[str(i)])

# ---- 工具 ----
def search_kb(query):
    r = col.query(query_texts=[query], n_results=2)
    return {"results": r["documents"][0]}

def get_weather(city):
    try:
        resp = requests.get(f"https://wttr.in/{city}?format=%C+%t", timeout=5)
        return {"city": city, "weather": resp.text.strip()}
    except:
        return {"city": city, "weather": "查询失败"}

def get_exchange_rate(from_currency, to_currency):
    try:
        resp = requests.get(f"https://api.frankfurter.app/latest?from={from_currency}&to={to_currency}", timeout=5)
        data = resp.json()
        return {"from": from_currency, "to": to_currency, "rate": data["rates"][to_currency], "date": data["date"]}
    except Exception as e:
        return {"error": str(e)}

tools = [
    {"name": "search_knowledge_base", "description": "搜索公司内部知识库",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "get_weather", "description": "获取实时天气",
     "input_schema": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}},
    {"name": "get_exchange_rate", "description": "查询实时汇率",
     "input_schema": {"type": "object", "properties": {"from_currency": {"type": "string"}, "to_currency": {"type": "string"}}, "required": ["from_currency", "to_currency"]}},
]
tool_map = {"search_knowledge_base": search_kb, "get_weather": get_weather, "get_exchange_rate": get_exchange_rate}

# ---- 核心对话函数 ----
client = anthropic.Anthropic()
SYSTEM = "你是极光科技助手小光，热情口语。需要查公司资料或实时数据时调用工具。"

def chat(message, history):
    messages = []
    # Gradio 6.x: history 是 list of dict
    for item in history:
        if isinstance(item, dict):
            messages.append(item)
        else:
            messages.append({"role": "user", "content": item[0]})
            messages.append({"role": "assistant", "content": item[1]})
    messages.append({"role": "user", "content": message})

    r = client.messages.create(
        model="claude-sonnet-4-6", max_tokens=400, thinking={"type": "disabled"},
        system=SYSTEM, tools=tools, messages=messages
    )

    reply = ""
    tool_log = []  # 记录调了哪些工具
    for block in r.content:
        if block.type == "text":
            reply = block.text
        elif block.type == "tool_use":
            name, args = block.name, block.input
            tool_log.append(f"🔧 {name}({json.dumps(args, ensure_ascii=False)})")
            result = tool_map[name](**args)

            messages.append({"role": "assistant", "content": [block]})
            messages.append({"role": "user", "content": [{
                "type": "tool_result", "tool_use_id": block.id,
                "content": json.dumps(result, ensure_ascii=False)
            }]})

            r2 = client.messages.create(
                model="claude-sonnet-4-6", max_tokens=400, thinking={"type": "disabled"},
                system=SYSTEM, tools=tools, messages=messages
            )
            for b2 in r2.content:
                if b2.type == "text":
                    reply = b2.text

    # 把工具调用信息拼到回复前面
    if tool_log:
        reply = "\n".join(tool_log) + "\n\n" + reply
    return reply or "（工具执行中...）"

# ---- 启动 ----
gr.ChatInterface(
    chat,
    title="极光科技智能助手",
    description="能查知识库 + 查天气 + 查汇率的 AI 助手",
).launch(share=True)
