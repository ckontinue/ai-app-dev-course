"""测试 config.py — 配置读取、默认值、类型转换"""

import sys
import os
import importlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ═══════════════════════════════════════════════════════════
# 硬编码常量（不依赖环境变量，直接测）
# ═══════════════════════════════════════════════════════════

def test_hardcoded_urls():
    """三个外部 API 地址是写死的，不该变"""
    import config
    importlib.reload(config)
    assert "wttr.in" in config.WEATHER_URL
    assert "frankfurter.app" in config.EXCHANGE_RATE_URL
    assert "mymemory.translated.net" in config.TRANSLATE_URL


def test_smtp_port():
    """SMTP 端口固定 465"""
    import config
    importlib.reload(config)
    assert config.SMTP_PORT == 465


def test_company_docs_file():
    """知识库文件名"""
    import config
    importlib.reload(config)
    assert config.COMPANY_DOCS_FILE == "company_docs.txt"


def test_log_constants():
    """日志目录、文件大小、备份数"""
    import config
    importlib.reload(config)
    assert config.LOG_DIR == "logs"
    assert config.LOG_MAX_BYTES == 10 * 1024 * 1024
    assert config.LOG_BACKUP_COUNT == 5


def test_log_file_path_join():
    """LOG_FILE 是 LOG_DIR + app.log 拼接"""
    import config
    importlib.reload(config)
    assert config.LOG_FILE == os.path.join("logs", "app.log")


# ═══════════════════════════════════════════════════════════
# 默认值测试（删掉环境变量后，看默认值对不对）
# ═══════════════════════════════════════════════════════════

def test_auth_token_default(monkeypatch):
    """没设环境变量 → 默认 '-'"""
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    import config
    importlib.reload(config)
    assert config.ANTHROPIC_AUTH_TOKEN == "-"


def test_base_url_default(monkeypatch):
    """没设环境变量 → 默认 Anthropic 官方地址"""
    monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
    import config
    importlib.reload(config)
    assert config.ANTHROPIC_BASE_URL == "https://api.anthropic.com"


def test_model_name_default(monkeypatch):
    """没设环境变量 → 默认 claude-sonnet-4-6"""
    monkeypatch.delenv("MODEL_NAME", raising=False)
    import config
    importlib.reload(config)
    assert config.MODEL_NAME == "claude-sonnet-4-6"


def test_smtp_defaults(monkeypatch):
    """没设环境变量 → SMTP 三项默认空字符串"""
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_USER", raising=False)
    monkeypatch.delenv("SMTP_PASS", raising=False)
    import config
    importlib.reload(config)
    assert config.SMTP_HOST == ""
    assert config.SMTP_USER == ""
    assert config.SMTP_PASS == ""


def test_http_timeout_default(monkeypatch):
    """没设 → HTTP_TIMEOUT 默认 10（int）"""
    monkeypatch.delenv("HTTP_TIMEOUT", raising=False)
    import config
    importlib.reload(config)
    assert config.HTTP_TIMEOUT == 10
    assert isinstance(config.HTTP_TIMEOUT, int)


def test_max_retries_default(monkeypatch):
    """没设 → MAX_RETRIES 默认 2（int）"""
    monkeypatch.delenv("MAX_RETRIES", raising=False)
    import config
    importlib.reload(config)
    assert config.MAX_RETRIES == 2
    assert isinstance(config.MAX_RETRIES, int)


def test_retry_backoff_default(monkeypatch):
    """没设 → RETRY_BACKOFF 默认 1.0（float）"""
    monkeypatch.delenv("RETRY_BACKOFF", raising=False)
    import config
    importlib.reload(config)
    assert config.RETRY_BACKOFF == 1.0
    assert isinstance(config.RETRY_BACKOFF, float)


def test_log_level_default(monkeypatch):
    """没设 → LOG_LEVEL 默认 INFO"""
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    import config
    importlib.reload(config)
    assert config.LOG_LEVEL == "INFO"


def test_gradio_port_default(monkeypatch):
    """没设 → GRADIO_PORT 默认 7860（int）"""
    monkeypatch.delenv("GRADIO_PORT", raising=False)
    import config
    importlib.reload(config)
    assert config.GRADIO_PORT == 7860
    assert isinstance(config.GRADIO_PORT, int)


def test_gradio_share_default(monkeypatch):
    """没设 → GRADIO_SHARE 默认 True"""
    monkeypatch.delenv("GRADIO_SHARE", raising=False)
    import config
    importlib.reload(config)
    assert config.GRADIO_SHARE is True


# ═══════════════════════════════════════════════════════════
# 环境变量读取测试（设了环境变量，看读没读到）
# ═══════════════════════════════════════════════════════════

def test_auth_token_from_env(monkeypatch):
    """设了环境变量 → 读到自定义值"""
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "sk-test123")
    import config
    importlib.reload(config)
    assert config.ANTHROPIC_AUTH_TOKEN == "sk-test123"


def test_model_name_from_env(monkeypatch):
    monkeypatch.setenv("MODEL_NAME", "deepseek-v4-pro")
    import config
    importlib.reload(config)
    assert config.MODEL_NAME == "deepseek-v4-pro"


def test_http_timeout_from_env(monkeypatch):
    """环境变量是字符串 → 转成 int"""
    monkeypatch.setenv("HTTP_TIMEOUT", "30")
    import config
    importlib.reload(config)
    assert config.HTTP_TIMEOUT == 30
    assert isinstance(config.HTTP_TIMEOUT, int)


def test_max_retries_from_env(monkeypatch):
    monkeypatch.setenv("MAX_RETRIES", "5")
    import config
    importlib.reload(config)
    assert config.MAX_RETRIES == 5


def test_retry_backoff_from_env(monkeypatch):
    """环境变量是字符串 → 转成 float"""
    monkeypatch.setenv("RETRY_BACKOFF", "2.5")
    import config
    importlib.reload(config)
    assert config.RETRY_BACKOFF == 2.5
    assert isinstance(config.RETRY_BACKOFF, float)


def test_log_level_from_env(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    import config
    importlib.reload(config)
    assert config.LOG_LEVEL == "DEBUG"


def test_gradio_port_from_env(monkeypatch):
    monkeypatch.setenv("GRADIO_PORT", "9999")
    import config
    importlib.reload(config)
    assert config.GRADIO_PORT == 9999


def test_gradio_share_false_from_env(monkeypatch):
    """GRADIO_SHARE='false' → bool 转换后是 False"""
    monkeypatch.setenv("GRADIO_SHARE", "false")
    import config
    importlib.reload(config)
    assert config.GRADIO_SHARE is False


def test_gradio_share_true_from_env(monkeypatch):
    """GRADIO_SHARE='true' → True"""
    monkeypatch.setenv("GRADIO_SHARE", "true")
    import config
    importlib.reload(config)
    assert config.GRADIO_SHARE is True


# ═══════════════════════════════════════════════════════════
# 边界情况
# ═══════════════════════════════════════════════════════════

def test_empty_string_env_var(monkeypatch):
    """环境变量设成空字符串 → 返回空字符串（不是默认值）"""
    monkeypatch.setenv("SMTP_HOST", "")
    import config
    importlib.reload(config)
    assert config.SMTP_HOST == ""


def test_smtp_all_empty_defaults(monkeypatch):
    """SMTP 三项都从空字符串开始"""
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_USER", raising=False)
    monkeypatch.delenv("SMTP_PASS", raising=False)
    import config
    importlib.reload(config)
    assert config.SMTP_HOST == config.SMTP_USER == config.SMTP_PASS == ""
