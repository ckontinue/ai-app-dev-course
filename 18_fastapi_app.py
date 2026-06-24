"""第十八课：FastAPI — 把手写应用包装成 REST API 接口

对比 13_engineered_app.py（Gradio 网页版）：
  Gradio — 自带前端界面，人在浏览器点按钮
  FastAPI — 纯后端接口，返回 JSON，给前端/App/别的程序调

新概念：
  @app.get/post  — 把 Python 函数挂到 URL 上（路由）
  Pydantic       — 定义请求/响应的"格式合同"，自动校验类型
  uvicorn        — 启动 HTTP 服务器（相当于 Gradio 的 launch()）
  CORS           — 允许跨域访问（接口和前端不在同一个地址时需要）
  /docs          — FastAPI 自动生成交互式 API 文档（Swagger）

跑起来后浏览器打开 http://localhost:9988/docs 就能在线调接口
"""

import os
import uuid
from datetime import datetime
from typing import Optional

import chromadb
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from pydantic import BaseModel, Field

import config as cfg
from logger import setup_logger
from utils import fail, ok, retry

# ═══════════════════════════════════════════════════════════
# 0. 日志
# ═══════════════════════════════════════════════════════════
log = setup_logger("fastapi", level=cfg.LOG_LEVEL, log_file=cfg.LOG_FILE,
                   max_bytes=cfg.LOG_MAX_BYTES, backup_count=cfg.LOG_BACKUP_COUNT)
log.info("FastAPI 应用启动中...")

# ═══════════════════════════════════════════════════════════
# 1. Pydantic 模型 — 定义"格式合同"
# ═══════════════════════════════════════════════════════════
# Pydantic 做什么？比如 ChatRequest 声明 message 是 str，那别人传 {"message": 123}
# 进来时 FastAPI 会自动拦下，返回 422 错误："message 应该是字符串，不是数字"
# 不用自己写 if not isinstance(msg, str) 了


class Message(BaseModel):
    """单条对话消息"""
    role: str = Field(description="角色：user（用户）或 assistant（AI）")
    content: str = Field(description="消息内容")


class ChatRequest(BaseModel):
    """POST /chat 的请求格式"""
    message: str = Field(min_length=1, description="用户刚发的最新消息")
    history: list[Message] = Field(
        default_factory=list,
        description="之前的对话历史，没有就传空列表"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="会话ID。不传自动生成新的，传了接着上次的聊"
    )


class ChatResponse(BaseModel):
    """POST /chat 的返回格式"""
    reply: str = Field(description="AI 的回复")
    session_id: str = Field(description="会话ID，下次请求带回来就能继续聊")
    timestamp: str = Field(description="回复时间")


class ErrorResponse(BaseModel):
    """出错时的返回格式"""
    detail: str = Field(description="错误说明")


# ═══════════════════════════════════════════════════════════
# 2. 创建 FastAPI 应用
# ═══════════════════════════════════════════════════════════
app = FastAPI(
    title="极光科技智能助手 API",
    description="5 工具 Agent：知识库 + 天气 + 汇率 + 翻译 + 发邮件",
    version="1.0.0",
)

# CORS — 允许任意来源调这个接口（开发阶段全开）
# 没有这一行，前端网页如果不在同一个端口，浏览器会拦截
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═══════════════════════════════════════════════════════════
# 3. 知识库 — 来自 13_engineered_app.py
# ═══════════════════════════════════════════════════════════
try:
    kc = chromadb.Client()
    col = kc.create_collection("knowledge_base")
    with open(cfg.COMPANY_DOCS_FILE, encoding="utf-8") as f:
        for i, chunk in enumerate(f.read().split("\n\n")):
            if chunk.strip():
                col.add(documents=[chunk.strip()], ids=[str(i)])
    log.info("知识库加载完成，共 %d 条", col.count())
except Exception as e:
    log.error("知识库加载失败: %s", e)
    raise

# ═══════════════════════════════════════════════════════════
# 4. 5 个工具 — 来自 13_engineered_app.py
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
# 5. Agent — 来自 13_engineered_app.py
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
# 6. 路由 — 把函数挂到 URL 上
# ═══════════════════════════════════════════════════════════


def extract_text(content):
    """从 LangChain 消息 content 里提取纯文本

    DeepSeek API 返回的 content 是列表（ThinkingBlock + TextBlock），
    Anthropic 原生返回的是字符串。这里兼容两种格式。
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                # DeepSeek 格式: {"type": "text", "text": "..."}
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
            elif hasattr(block, "text"):
                # Anthropic SDK 格式: TextBlock(text="...")
                parts.append(block.text)
        return "".join(parts)
    return str(content)


@app.get("/")
async def root():
    """首页 — 检查服务是否在运行"""
    return {
        "service": "极光科技智能助手 API",
        "version": "1.0.0",
        "tools": [t.name for t in TOOLS],
        "model": cfg.MODEL_NAME,
        "docs": "/docs",
    }


@app.get("/tools")
async def list_tools():
    """列出所有可用工具及说明"""
    return {
        "tools": [
            {"name": t.name, "description": t.description}
            for t in TOOLS
        ]
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """主聊天接口 — 发消息，拿回复

    用法示例（curl）：
      curl -X POST http://localhost:9988/chat \\
        -H "Content-Type: application/json" \\
        -d '{"message": "北京天气怎么样？", "history": []}'

    用法示例（Python）：
      import requests
      resp = requests.post("http://localhost:9988/chat", json={
          "message": "北京天气怎么样？",
          "history": []
      })
      print(resp.json()["reply"])
    """
    sid = request.session_id or uuid.uuid4().hex[:8]
    log.info("[%s] 收到消息: %s", sid, request.message[:80])

    try:
        # 把历史转成 LangChain 消息格式
        messages = []
        for item in request.history:
            if item.role == "user":
                messages.append(HumanMessage(content=item.content))
            else:
                messages.append(AIMessage(content=item.content))
        messages.append(HumanMessage(content=request.message))

        # 调 Agent
        result = agent.invoke({"messages": messages})

        # 提取最后一条 AI 回复
        reply = ""
        for msg in reversed(result["messages"]):
            if isinstance(msg, AIMessage) and msg.content:
                text = extract_text(msg.content)
                if not text:
                    continue
                # 如果 Agent 调了工具，附上工具名
                tool_info = ""
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        tool_info += f"🔧 {tc['name']}\n"
                reply = (tool_info + text) if tool_info else text
                break

        if not reply:
            reply = "（Agent 处理中，未生成回复）"

        log.info("[%s] 回复: %s", sid, reply[:80])

        return ChatResponse(
            reply=reply,
            session_id=sid,
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        log.exception("[%s] Agent 调用异常", sid)
        raise HTTPException(
            status_code=500,
            detail=f"AI 服务异常（{type(e).__name__}）：{e}"
        )


# ═══════════════════════════════════════════════════════════
# 7. 启动 — 换成 uvicorn 而不是 Gradio 的 launch()
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("API_PORT", 9988))
    log.info("=" * 50)
    log.info("FastAPI 版助手启动")
    log.info("模型: %s | 工具: %d个 | 重试: %d次",
             cfg.MODEL_NAME, len(TOOLS), cfg.MAX_RETRIES)
    log.info("API 地址: http://localhost:%d", port)
    log.info("交互文档: http://localhost:%d/docs", port)
    log.info("=" * 50)

    uvicorn.run(app, host="0.0.0.0", port=port)
