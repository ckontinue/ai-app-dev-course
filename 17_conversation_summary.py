"""第十七课：用 AI 自动总结对话重点

之前 15/16 课只能统计"多少条、多长"这些数字。
本课让 LLM 读对话内容，自动提炼：
  1. 都在聊什么话题
  2. 用户最关心什么
  3. 助手的不足在哪里

简单说：用 AI 分析 AI 的聊天记录，生成一份人工能看的摘要报告。
"""

import sqlite3
import anthropic
import json

client = anthropic.Anthropic()
DB_PATH = "conversations.db"

# ═══════════════════════════════════════════════════════════
# 1. 读取对话数据
# ═══════════════════════════════════════════════════════════
def load_conversations(limit=100, keyword=None):
    conn = sqlite3.connect(DB_PATH)
    if keyword:
        rows = conn.execute(
            "SELECT role, content, created_at FROM conversations "
            "WHERE content LIKE ? ORDER BY id LIMIT ?",
            (f"%{keyword}%", limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT role, content, created_at FROM conversations ORDER BY id LIMIT ?",
            (limit,)
        ).fetchall()
    conn.close()

    # 拼成一段文本
    text = ""
    for role, content, ts in rows:
        label = "用户" if role == "user" else "助手"
        text += f"[{ts}] {label}：{content}\n\n"
    return text, len(rows)

# ═══════════════════════════════════════════════════════════
# 2. 发给 LLM 做总结
# ═══════════════════════════════════════════════════════════
SUMMARY_PROMPT = """你是一个对话数据分析师。下面是一段 AI 客服和用户的对话记录。
请分析并输出一份简洁报告，包含以下四部分（用 Markdown 格式）：

## 🔥 热门话题 TOP5
列出聊得最多的 5 个话题，每个一句话说明。

## 👤 用户画像
从对话中推断：用户是什么角色？对什么感兴趣？技术水平如何？

## 💡 用户关心什么
列出用户反复问或追问的点，说明他真正想了解什么。

## ⚠️ 助手不足
助手回复有没有答非所问、重复啰嗦、或明显没帮到用户的地方？

---
以下是对话记录：
"""

def summarize(text):
    r = client.messages.create(
        model="deepseek-v4-pro",
        max_tokens=1000,
        temperature=0.3,
        system="你是数据分析师，输出简洁、有洞察的报告，使用中文。",
        messages=[{
            "role": "user",
            "content": SUMMARY_PROMPT + text
        }]
    )
    # DeepSeek 返回的 content 里混了 ThinkingBlock 和 TextBlock，
    # 只取 .text 的部分（跳过思考过程）
    for block in r.content:
        if hasattr(block, "text"):
            return block.text
    return "（未能提取回复）"

# ═══════════════════════════════════════════════════════════
# 3. 主流程
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys
    keyword = sys.argv[1] if len(sys.argv) > 1 else None

    if keyword:
        print(f"🔍 筛选关键词：{keyword}")

    print("📖 正在读取对话记录...")
    conversations, total = load_conversations(keyword=keyword)

    if total == 0:
        print("❌ 没有对话记录")
        exit()

    print(f"   共 {total} 条记录，共 {len(conversations)} 字符")

    print("🤖 AI 正在分析...")
    report = summarize(conversations)

    print("\n" + "=" * 50)
    print("📊 对话分析报告")
    print("=" * 50)
    print(report)

    # 保存为文件
    with open("conversation_report.md", "w", encoding="utf-8") as f:
        f.write("# AI 对话分析报告\n\n")
        f.write(f"共分析 {total} 条对话记录\n\n")
        f.write(report)

    print("\n✅ 报告已保存为 conversation_report.md")
