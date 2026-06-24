"""第十四课：邮件助手 — 写稿 + 翻译 + 发送一条龙

场景：你说中文需求，AI 帮你：
  1. 起草邮件正文（你审阅确认）
  2. 如果目标是外文 → 自动翻译
  3. 确认后发送

对比 13 课（通用助手 5 工具任选）：
  13 课 = 瑞士军刀，AI 自己判断用哪个工具
  14 课 = 专用扳手，加了"工作流"——AI 知道邮件任务必须走 写→译→发 三站
"""

import gradio as gr
import requests
from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool

import config as cfg
from logger import setup_logger
from utils import fail, ok, retry

log = setup_logger("email", level=cfg.LOG_LEVEL, log_file=cfg.LOG_FILE,
                   max_bytes=cfg.LOG_MAX_BYTES, backup_count=cfg.LOG_BACKUP_COUNT)
log.info("邮件助手启动")

# ═══════════════════════════════════════════════════════════
# 工具 1：翻译（和之前一样，保留）
# ═══════════════════════════════════════════════════════════


@tool
@retry(max_retries=cfg.MAX_RETRIES, backoff=cfg.RETRY_BACKOFF)
def translate_text(text: str, target_lang: str) -> str:
    """翻译文本。source_lang 源语言(zh/en/ja/ko), target_lang 目标语言(zh/en/ja/ko)"""
    log.info("翻译: %s→%s (%d字)", source_lang, target_lang, len(text))
    code_map = {"zh": "zh-CN", "en": "en", "ja": "ja", "ko": "ko"}
    src = code_map.get(source_lang, source_lang)
    tgt = code_map.get(target_lang, target_lang)
    resp = requests.get(
        cfg.TRANSLATE_URL,
        params={"q": text, "langpair": f"{src}|{tgt}"},
        timeout=cfg.HTTP_TIMEOUT)
    translated = resp.json()["responseData"]["translatedText"]
    return ok({"original": text,
               "source_lang": source_lang, "target_lang": target_lang,
               "translated": translated})


# ═══════════════════════════════════════════════════════════
# 工具 2：发邮件
# ═══════════════════════════════════════════════════════════


@tool
def send_email(to: str, subject: str, body: str) -> str:
    """发邮件。调用此工具前必须向用户确认收件人、主题、正文三项都无误。"""
    log.info("发送: to=%s subj=%s", to, subject)

    if not all([cfg.SMTP_HOST, cfg.SMTP_USER, cfg.SMTP_PASS]):
        log.warning("SMTP 未配置")
        return fail(
            "邮件功能未配置，请先设置环境变量",
            "SMTP_HOST SMTP_USER SMTP_PASS",
            QQ邮箱="smtp.qq.com，授权码在 QQ邮箱→设置→账户→POP3/SMTP 获取",
            Gmail="smtp.gmail.com，需开启两步验证+应用专用密码")

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
        log.info("发送成功: %s", to)
        return ok({"to": to, "subject": subject}, message="邮件已发送")
    except Exception as e:
        log.error("发送失败: %s", e)
        return fail(f"发送失败: {e}")


TOOLS = [translate_text, send_email]

# ═══════════════════════════════════════════════════════════
# Agent — 系统提示词定义了"工作流"
# ═══════════════════════════════════════════════════════════

model = ChatAnthropic(
    model=cfg.MODEL_NAME,
    api_key=cfg.ANTHROPIC_AUTH_TOKEN,
    base_url=cfg.ANTHROPIC_BASE_URL,
)

SYSTEM = """你是"邮件助手小邮"，帮用户写邮件、翻译、发送。

工作流程（必须按顺序，不能跳步）：

第1步 — 理解需求：
  用户可能说"给XX发封邮件说YY"，你需要确认三点：
  - 收件人邮箱地址？（如果没有，主动问）
  - 主题是什么？
  - 内容要点？

第2步 — 起草正文：
  根据用户的要点，写一封得体的邮件正文。
  写完先给用户看，等用户说"可以"或"发吧"再继续。

第3步 — 翻译（如果需要）：
  如果收件人用外文（英文/日文/韩文等），调用 translate_text。
  必须指定 source_lang（用户语言，通常是 zh）和 target_lang（收件人语言）。
  翻完给用户确认。

第4步 — 发送：
  三项（收件人、主题、正文）都确认后，调用 send_email。

注意：
- 不要在用户确认前直接发送，必须等用户说"发"
- 如果 SMTP 未配置，告诉用户怎么设置（QQ邮箱/Gmail）
"""

agent = create_agent(model, TOOLS, system_prompt=SYSTEM)
log.info("Agent 就绪")

# ═══════════════════════════════════════════════════════════
# Gradio 界面
# ═══════════════════════════════════════════════════════════


def build_messages(history, new_message):
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
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage) and msg.content:
            # 提取文本 — 兼容两种格式：
            #   纯字符串: "你好"        → 直接用
            #   结构化列表: [{type: text, text: "..."}, ...] → 拼 text 块
            content = msg.content
            if isinstance(content, list):
                texts = [b["text"] for b in content
                         if isinstance(b, dict) and b.get("type") == "text"]
                content = "\n".join(texts)

            if not content:
                continue

            tool_info = ""
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_info += f"🔧 {tc['name']}\n"
            return (tool_info + content) if tool_info else content
    return "（处理中...）"


def chat(message, history):
    log.info("用户: %s", message[:100])

    try:
        messages = build_messages(history, message)
        result = agent.invoke({"messages": messages})
        reply = extract_reply(result)
        log.info("回复: %s", reply[:100])
        return reply
    except Exception as e:
        log.exception("异常")
        return f"抱歉，出了一点问题（{type(e).__name__}），请稍后再试。"


if __name__ == "__main__":
    smtp_ready = all([cfg.SMTP_HOST, cfg.SMTP_USER, cfg.SMTP_PASS])
    log.info("SMTP: %s", "已配置" if smtp_ready else "未配置（可演示写稿+翻译，发送需配置）")

    gr.ChatInterface(
        chat,
        title="邮件助手 (14课)",
        description=(
            "写稿 + 翻译 + 发送，一条龙\n"
            f"SMTP: {'已配置 ✅' if smtp_ready else '未配置 ⚠️（发送功能暂不可用）'}"
        ),
        examples=[
            "帮我给 john@company.com 发邮件，告诉他项目延期到下周，用英文",
            "给老板发邮件请假，明天家里有事",
            "帮我写一封日文邮件给 tanaka@example.com，感谢他上周的接待",
        ],
    ).launch(server_port=cfg.GRADIO_PORT, share=cfg.GRADIO_SHARE)
