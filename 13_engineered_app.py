"""第十三课：工程化 — 日志 + 配置分离 + 统一错误处理 + 重试

对比 12_langchain_app.py 加了什么：
  1. 日志 — 每条操作都有时间戳记录，出问题能溯源
  2. 配置分离 — 所有参数集中在 config.py，改配置不碰代码
  3. 统一错误处理 — ok()/fail() 格式统一，chat 函数有保护
  4. 重试机制 — 网络抖动自动重试，指数退避
"""

import json

import chromadb
import gradio as gr
import requests
from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool

import config as cfg
from logger import setup_logger
from utils import fail, ok, retry

# ═══════════════════════════════════════════════════════════
# 0. 日志 — 控制台 + 文件双输出
# ═══════════════════════════════════════════════════════════
log = setup_logger("app", level=cfg.LOG_LEVEL, log_file=cfg.LOG_FILE,
                   max_bytes=cfg.LOG_MAX_BYTES, backup_count=cfg.LOG_BACKUP_COUNT)
log.info("应用启动，加载知识库...")

# ═══════════════════════════════════════════════════════════
# 1. 知识库
# ═══════════════════════════════════════════════════════════
try:
    kc = chromadb.Client()
    col = kc.create_collection("knowledge_base")
    with open(cfg.COMPANY_DOCS_FILE, encoding="utf-8") as f:
        for i, c in enumerate(f.read().split("\n\n")):
            if c.strip():
                col.add(documents=[c.strip()], ids=[str(i)])
    log.info("知识库加载完成，共 %d 条", col.count())
except Exception as e:
    log.error("知识库加载失败: %s", e)
    raise

# ═══════════════════════════════════════════════════════════
# 2. 5 个工具 — 每个都加了 @retry + ok()/fail() + 日志
# ═══════════════════════════════════════════════════════════


@tool
@retry(max_retries=cfg.MAX_RETRIES, backoff=cfg.RETRY_BACKOFF)
def search_knowledge_base(query: str) -> str:
    """搜索公司内部知识库，查政策、规定、产品信息"""
    log.info("知识库查询: %s", query)
    r = col.query(query_texts=[query], n_results=2)
    results = r["documents"][0]
    log.debug("命中 %d 条", len(results))
    return ok(results)


@tool
@retry(max_retries=cfg.MAX_RETRIES, backoff=cfg.RETRY_BACKOFF)
def get_weather(city: str) -> str:
    """查实时天气，city 用英文名如 Beijing、Tokyo"""
    log.info("天气查询: %s", city)
    resp = requests.get(
        cfg.WEATHER_URL.format(city=city), timeout=cfg.HTTP_TIMEOUT)
    weather = resp.text.strip()
    log.debug("天气结果: %s", weather)
    return ok({"city": city, "weather": weather})


@tool
@retry(max_retries=cfg.MAX_RETRIES, backoff=cfg.RETRY_BACKOFF)
def get_exchange_rate(from_currency: str, to_currency: str) -> str:
    """查实时汇率，货币代码用 USD/CNY/EUR/JPY 等三个字母"""
    log.info("汇率查询: %s→%s", from_currency, to_currency)
    resp = requests.get(
        cfg.EXCHANGE_RATE_URL,
        params={"from": from_currency, "to": to_currency},
        timeout=cfg.HTTP_TIMEOUT)
    data = resp.json()
    return ok({
        "from": from_currency, "to": to_currency,
        "rate": data["rates"][to_currency], "date": data["date"]
    })


@tool
@retry(max_retries=cfg.MAX_RETRIES, backoff=cfg.RETRY_BACKOFF)
def translate_text(text: str, source_lang: str, target_lang: str) -> str:
    """翻译文本。source_lang 源语言(zh/en/ja/ko), target_lang 目标语言(zh/en/ja/ko)"""
    log.info("翻译请求: %s→%s (%d字)", source_lang, target_lang, len(text))
    code_map = {"zh": "zh-CN", "en": "en", "ja": "ja", "ko": "ko"}
    src = code_map.get(source_lang, source_lang)
    tgt = code_map.get(target_lang, target_lang)
    resp = requests.get(
        cfg.TRANSLATE_URL,
        params={"q": text, "langpair": f"{src}|{tgt}"},
        timeout=cfg.HTTP_TIMEOUT)
    translated = resp.json()["responseData"]["translatedText"]
    log.debug("翻译完成: %s", translated[:50])
    return ok({"original": text,
               "source_lang": source_lang, "target_lang": target_lang,
               "translated": translated})


@tool
def send_email(to: str, subject: str, body: str) -> str:
    """发邮件。需要先设置 SMTP 环境变量（QQ邮箱/Gmail 都支持）"""
    log.info("发邮件: to=%s, subject=%s", to, subject)

    if not all([cfg.SMTP_HOST, cfg.SMTP_USER, cfg.SMTP_PASS]):
        log.warning("邮件未配置，返回提示")
        return fail(
            "邮件功能未配置",
            "请设环境变量: SMTP_HOST SMTP_USER SMTP_PASS",
            QQ邮箱="SMTP_HOST=smtp.qq.com, 授权码在 QQ邮箱→设置→账户→POP3/SMTP",
            Gmail="SMTP_HOST=smtp.gmail.com, 需开启两步验证+应用专用密码")

    import smtplib
    from email.mime.text import MIMEText

    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = cfg.SMTP_USER
    msg["To"] = to
    msg["Subject"] = subject

    try:
        server = smtplib.SMTP_SSL(cfg.SMTP_HOST, cfg.SMTP_PORT, timeout=10)
        server.login(cfg.SMTP_USER, cfg.SMTP_PASS)
        server.sendmail(cfg.SMTP_USER, [to], msg.as_string())
        server.quit()
        log.info("邮件发送成功")
        return ok({"to": to, "subject": subject}, message="发送成功")
    except Exception as e:
        log.error("邮件发送失败: %s", e)
        return fail(f"发送失败: {e}")


TOOLS = [search_knowledge_base, get_weather, get_exchange_rate,
         translate_text, send_email]

# ═══════════════════════════════════════════════════════════
# 3. LangChain Agent
# ═══════════════════════════════════════════════════════════
try:
    model = ChatAnthropic(
        model=cfg.MODEL_NAME,
        api_key=cfg.ANTHROPIC_AUTH_TOKEN,
        base_url=cfg.ANTHROPIC_BASE_URL,
    )
    log.info("模型初始化: %s @ %s", cfg.MODEL_NAME, cfg.ANTHROPIC_BASE_URL)
except Exception as e:
    log.error("模型初始化失败: %s", e)
    raise

SYSTEM = (
    "你是极光科技助手小光，热情口语。"
    "需要资料查 search_knowledge_base、天气查 get_weather、"
    "汇率查 get_exchange_rate、翻译用 translate_text、"
    "发邮件用 send_email。"
)

agent = create_agent(model, TOOLS, system_prompt=SYSTEM)
log.info("Agent 创建完成，工具: %s", [t.name for t in TOOLS])

# ═══════════════════════════════════════════════════════════
# 4. Gradio 网页 — chat 函数加了错误保护
# ═══════════════════════════════════════════════════════════


def build_messages(history, new_message):
    """把 Gradio history 转成 LangChain 消息列表"""
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
            messages.append(HumanMessage(content=item[0]))
            if len(item) > 1 and item[1]:
                messages.append(AIMessage(content=item[1]))
    messages.append(HumanMessage(content=new_message))
    return messages


def extract_reply(result):
    """从 Agent 返回中提取最后一条 AI 消息"""
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage) and msg.content:
            tool_info = ""
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_info += f"🔧 {tc['name']}\n"
            return (tool_info + msg.content) if tool_info else msg.content
    return "（处理中...）"


def chat(message, history):
    """聊天入口 — 加错误保护，用户永远不会看到 traceback"""
    log.info("收到消息: %s", message[:80])

    try:
        messages = build_messages(history, message)
        result = agent.invoke({"messages": messages})
        reply = extract_reply(result)
        log.info("回复: %s", reply[:80])
        return reply

    except Exception as e:
        log.exception("Agent 调用异常")
        return (
            f"抱歉，出了一点问题（{type(e).__name__}），请稍后再试。\n\n"
            f"提示：{e}"
        )


if __name__ == "__main__":
    log.info("=" * 50)
    log.info("工程化版助手启动")
    log.info("模型: %s | 重试: %d次 | 超时: %ds",
             cfg.MODEL_NAME, cfg.MAX_RETRIES, cfg.HTTP_TIMEOUT)
    log.info("日志文件: %s", cfg.LOG_FILE)

    gr.ChatInterface(
        chat,
        title="极光科技智能助手 (工程化版)",
        description=(
            "LangChain Agent | 5 工具：知识库 + 天气 + 汇率 + 翻译 + 发邮件\n"
            "工程化：日志追踪 + 自动重试 + 统一错误处理"
        ),
    ).launch(server_port=cfg.GRADIO_PORT, share=cfg.GRADIO_SHARE)
