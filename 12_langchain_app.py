"""第十二课：LangChain 重写 — 同样的功能，不同的写法

对比 10_web_app.py（手写 Agent 循环 35 行）：
  LangChain 帮你做三件事：
    1. AI 说"我要用XX工具" → 自动识别，不写 if/elif
    2. 工具执行完 → 自动把结果拼回对话
    3. AI 说"还要再用工具" → 自动循环，直到 AI 说"好了这是最终答案"

  就像打车：
    10 课 = 你自己开车（踩离合→挂挡→油门→看路→刹车）
    12 课 = 叫滴滴（说目的地→上车→到了下车）
"""

import os, json, chromadb, requests, gradio as gr

from langchain_anthropic import ChatAnthropic
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage

# ═══════════════════════════════════════════════════════════
# 1. 知识库（和 10 课一模一样，没变）
# ═══════════════════════════════════════════════════════════
kc = chromadb.Client()
col = kc.create_collection("knowledge_base")
with open("company_docs.txt", encoding="utf-8") as f:
    for i, c in enumerate(f.read().split("\n\n")):
        if c.strip():
            col.add(documents=[c.strip()], ids=[str(i)])

# ═══════════════════════════════════════════════════════════
# 2. 5 个工具（用 @tool 装饰器，比 10 课少写 40 行 schema）
# ═══════════════════════════════════════════════════════════

@tool
def search_knowledge_base(query: str) -> str:
    """搜索公司内部知识库，查政策、规定、产品信息"""
    r = col.query(query_texts=[query], n_results=2)
    return json.dumps({"results": r["documents"][0]}, ensure_ascii=False)


@tool
def get_weather(city: str) -> str:
    """查实时天气，city 用英文名如 Beijing、Tokyo"""
    try:
        resp = requests.get(
            f"https://wttr.in/{city}?format=%C+%t", timeout=5)
        return json.dumps({"city": city, "weather": resp.text.strip()},
                          ensure_ascii=False)
    except:
        return json.dumps({"city": city, "weather": "查询失败"},
                          ensure_ascii=False)


@tool
def get_exchange_rate(from_currency: str, to_currency: str) -> str:
    """查实时汇率，货币代码用 USD/CNY/EUR/JPY 等三个字母"""
    try:
        resp = requests.get(
            f"https://api.frankfurter.app/latest?from={from_currency}&to={to_currency}",
            timeout=5)
        data = resp.json()
        return json.dumps({
            "from": from_currency, "to": to_currency,
            "rate": data["rates"][to_currency], "date": data["date"]
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@tool
def translate_text(text: str, target_lang: str) -> str:
    """翻译文本。target_lang: zh(中文) en(英文) ja(日文) ko(韩文)"""
    lang_map = {"zh": "zh-CN", "en": "en", "ja": "ja", "ko": "ko"}
    tl = lang_map.get(target_lang, target_lang)
    try:
        resp = requests.get(
            "https://api.mymemory.translated.net/get",
            params={"q": text, "langpair": f"Auto|{tl}"},
            timeout=10)
        data = resp.json()
        return json.dumps({
            "original": text,
            "target_lang": target_lang,
            "translated": data["responseData"]["translatedText"]
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@tool
def send_email(to: str, subject: str, body: str) -> str:
    """发邮件。需要先设置 SMTP 环境变量（QQ邮箱/Gmail 都支持）"""
    smtp_host = os.environ.get("SMTP_HOST", "")
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")

    if not all([smtp_host, smtp_user, smtp_pass]):
        return json.dumps({
            "error": "邮件功能未配置",
            "help": "请设环境变量: SMTP_HOST SMTP_USER SMTP_PASS",
            "QQ邮箱": "SMTP_HOST=smtp.qq.com, 授权码在 QQ邮箱→设置→账户→POP3/SMTP 获取",
            "Gmail": "SMTP_HOST=smtp.gmail.com, 需开启两步验证+应用专用密码"
        }, ensure_ascii=False)

    import smtplib
    from email.mime.text import MIMEText

    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = smtp_user
    msg["To"] = to
    msg["Subject"] = subject

    try:
        server = smtplib.SMTP_SSL(smtp_host, 465, timeout=10)
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, [to], msg.as_string())
        server.quit()
        return json.dumps({"success": True, "to": to, "subject": subject},
                          ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


TOOLS = [search_knowledge_base, get_weather, get_exchange_rate,
         translate_text, send_email]

# ═══════════════════════════════════════════════════════════
# 3. LangChain Agent（替代手写 35 行循环的关键！）
# ═══════════════════════════════════════════════════════════
model = ChatAnthropic(
    model="claude-sonnet-4-6",
    api_key=os.environ.get("ANTHROPIC_AUTH_TOKEN", "-"),
    base_url=os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
)

SYSTEM = (
    "你是极光科技助手小光，热情口语。"
    "需要资料查 search_knowledge_base、天气查 get_weather、"
    "汇率查 get_exchange_rate、翻译用 translate_text、"
    "发邮件用 send_email。"
)

# ====== 10 课的 35 行 Agent 循环，现在 1 行 ======
agent = create_agent(model, TOOLS, system_prompt=SYSTEM)
# =================================================

# ═══════════════════════════════════════════════════════════
# 4. Gradio 网页（和 10 课一毛一样的界面）
# ═══════════════════════════════════════════════════════════
def chat(message, history):
    # history 转成 LangChain 消息格式
    messages = []
    for item in history:
        if isinstance(item, dict):
            role = item.get("role", "user")
            content = item.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            else:
                messages.append(AIMessage(content=content))
        else:
            # 老格式兼容
            messages.append(HumanMessage(content=item[0]))
            if len(item) > 1 and item[1]:
                messages.append(AIMessage(content=item[1]))

    messages.append(HumanMessage(content=message))

    # ====== 原来的 35 行循环，这里 1 行完事 ======
    result = agent.invoke({"messages": messages})
    # ===========================================

    # 取最后一条 AI 消息（中间的工具调用消息自动被 LangChain 过滤）
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage) and msg.content:
            # 展示工具调用记录
            tool_info = ""
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_info += f"🔧 {tc['name']}\n"
            return (tool_info + msg.content) if tool_info else msg.content

    return "（处理中...）"


if __name__ == "__main__":
    print("🚀 LangChain 版助手启动中...")
    print(f"   模型：{model.model}")
    print(f"   工具：{', '.join(t.name for t in TOOLS)}")
    print()
    print("   对比 10_web_app.py：")
    print("   手写 Agent 循环 35 行 → create_react_agent 1 行")
    print("   手写 JSON Schema 40 行 → @tool 装饰器自动生成")
    print("   手写 tool_map 字典      → LangChain 自动管理")
    print()

    gr.ChatInterface(
        chat,
        title="极光科技智能助手 (LangChain版)",
        description="LangChain Agent | 5 工具：知识库 + 天气 + 汇率 + 翻译 + 发邮件",
    ).launch(share=True)
