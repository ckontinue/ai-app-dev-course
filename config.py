"""集中配置 — 改参数不用改代码"""

import os

# ── LLM ────────────────────────────────────────────
ANTHROPIC_AUTH_TOKEN = os.environ.get("ANTHROPIC_AUTH_TOKEN", "-")
ANTHROPIC_BASE_URL = os.environ.get(
    "ANTHROPIC_BASE_URL", "https://api.anthropic.com")
MODEL_NAME = os.environ.get("MODEL_NAME", "claude-sonnet-4-6")

# ── 知识库 ─────────────────────────────────────────
COMPANY_DOCS_FILE = "company_docs.txt"

# ── 外部 API ───────────────────────────────────────
WEATHER_URL = "https://wttr.in/{city}?format=%C+%t"
EXCHANGE_RATE_URL = "https://api.frankfurter.app/latest"
TRANSLATE_URL = "https://api.mymemory.translated.net/get"

# ── 邮件 ───────────────────────────────────────────
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
SMTP_PORT = 465

# ── HTTP ───────────────────────────────────────────
HTTP_TIMEOUT = int(os.environ.get("HTTP_TIMEOUT", 10))
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", 2))
RETRY_BACKOFF = float(os.environ.get("RETRY_BACKOFF", 1.0))

# ── 日志 ───────────────────────────────────────────
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "app.log")
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5

# ── Gradio ─────────────────────────────────────────
GRADIO_PORT = int(os.environ.get("GRADIO_PORT", 7860))
GRADIO_SHARE = os.environ.get("GRADIO_SHARE", "true").lower() == "true"
