"""第十一课：给助手加 SQLite 数据库 — 对话持久化

三层架构对比：
  05/06：知识 = 拼进 system prompt（一次性，关了就没）
  09  ：知识 = 工具检索（AI 决定查不查，但对话记录关了就没）
  11  ：知识 = 工具检索 + SQLite 持久化（对话永远保存，关了还能查）

SQLite 是什么？
  一个轻量数据库，数据存在一个 .db 文件里。
  不需要装软件，Python 自带 sqlite3 模块。
  类比：一个 Excel 文件，你的对话就是一张表里的行。
"""

import anthropic, chromadb, json, sqlite3, os
from datetime import datetime

client = anthropic.Anthropic()

# ═══════════════════════════════════════════════════════════
# 1. 知识库（ChromaDB，不动）
# ═══════════════════════════════════════════════════════════
kc = chromadb.Client()
col = kc.create_collection("kb_main")
with open("company_docs.txt", encoding="utf-8") as f:
    for i, c in enumerate(f.read().split("\n\n")):
        if c.strip():
            col.add(documents=[c.strip()], ids=[str(i)])

# ═══════════════════════════════════════════════════════════
# 2. SQLite 数据库（新增）
# ═══════════════════════════════════════════════════════════
DB_PATH = "conversations.db"

# 如果数据库不存在，自动创建
conn = sqlite3.connect(DB_PATH)
conn.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT NOT NULL,       -- 'user' 或 'assistant'
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
conn.commit()

def save_message(role, content):
    """每句对话都存进 SQLite"""
    # 过滤掉终端产生的非法 Unicode 字符（方向键、复制粘贴乱码）
    content = content.encode("utf-8", errors="replace").decode("utf-8")
    conn.execute(
        "INSERT INTO conversations (role, content) VALUES (?, ?)",
        (role, content)
    )
    conn.commit()

def search_history(query):
    """搜索历史对话"""
    rows = conn.execute(
        "SELECT role, content, created_at FROM conversations "
        "WHERE content LIKE ? ORDER BY created_at DESC LIMIT 5",
        (f"%{query}%",)
    ).fetchall()
    if not rows:
        return {"results": [], "message": "没有找到相关历史记录"}
    return {"results": [
        {"role": r, "content": c[:80], "time": t}
        for r, c, t in rows
    ]}

# ═══════════════════════════════════════════════════════════
# 3. 工具箱（4 个工具）
# ═══════════════════════════════════════════════════════════
def get_weather(city):
    import requests
    try:
        resp = requests.get(f"https://wttr.in/{city}?format=%C+%t", timeout=5)
        return {"city": city, "weather": resp.text.strip()}
    except:
        return {"city": city, "weather": "查询失败"}

tools = [
    {
        "name": "search_knowledge_base",
        "description": "搜索公司内部知识库",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"]
        }
    },
    {
        "name": "get_weather",
        "description": "获取实时天气",
        "input_schema": {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"]
        }
    },
    {
        "name": "search_history",
        "description": "搜索历史对话记录，比如用户之前问过什么",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "搜索词"}},
            "required": ["query"]
        }
    }
]

TOOLS_MAP = {
    "search_knowledge_base": lambda query: {"results": col.query(query_texts=[query], n_results=2)["documents"][0]},
    "get_weather": get_weather,
    "search_history": search_history,
}

# ═══════════════════════════════════════════════════════════
# 4. 主循环
# ═══════════════════════════════════════════════════════════
SYSTEM = "你是极光科技助手小光，热情口语。需要资料、天气、历史对话时调用对应工具。"

history = []
print("🤖 极光助手 SQLite 版已上线（/quit 退出）")
print("   💾 对话自动保存到 conversations.db")
print("   🛠 4 个工具：查资料 / 查天气 / 查汇率 / 查历史\n")

while True:
    user = input("你：")
    if user == "/quit":
        break

    # 存入 SQLite
    save_message("user", user)

    history.append({"role": "user", "content": user})

    r = client.messages.create(
        model="deepseek-v4-pro", max_tokens=400, thinking={"type": "disabled"},
        system=SYSTEM, tools=tools, messages=history
    )

    reply = ""
    tool_log = []
    for block in r.content:
        if block.type == "text":
            reply = block.text
        elif block.type == "tool_use":
            name, args = block.name, block.input
            tool_log.append(f"🔧 {name}({json.dumps(args, ensure_ascii=False)})")
            result = TOOLS_MAP[name](**args)

            history.append({"role": "assistant", "content": [block]})
            history.append({"role": "user", "content": [{
                "type": "tool_result", "tool_use_id": block.id,
                "content": json.dumps(result, ensure_ascii=False)
            }]})

            r2 = client.messages.create(
                model="deepseek-v4-pro", max_tokens=400, thinking={"type": "disabled"},
                system=SYSTEM, tools=tools, messages=history
            )
            for b2 in r2.content:
                if b2.type == "text":
                    reply = b2.text
                    history.append({"role": "assistant", "content": b2.text})

    if reply:
        for t in tool_log:
            print(f"  {t}")
        print(f"小光：{reply}\n")

        # 存入 SQLite
        if tool_log:
            save_message("assistant", "\n".join(tool_log) + "\n" + reply)
        else:
            save_message("assistant", reply)

# ═══════════════════════════════════════════════════════════
# 5. 退出后展示数据库里有啥
# ═══════════════════════════════════════════════════════════
print(f"\n📊 数据库文件：{DB_PATH}")
print(f"   大小：{os.path.getsize(DB_PATH)} bytes")

rows = conn.execute("SELECT role, content, created_at FROM conversations ORDER BY id").fetchall()
print(f"   共 {len(rows)} 条记录：")
for r in rows:
    role_label = "🧑" if r[0] == "user" else "🤖"
    print(f"   {role_label} [{r[2]}] {r[1][:60]}...")

conn.close()
print("\n💡 你可以用任何 SQLite 工具打开 conversations.db 查看")
print("   命令行：sqlite3 conversations.db 'SELECT * FROM conversations;'")
