"""工具函数 — 重试 + 统一返回格式"""

import time
import json
from functools import wraps


def retry(max_retries=2, backoff=1.0):
    """指数退避重试装饰器

    第1次失败 → 等 backoff 秒 → 第2次失败 → 等 backoff*2 秒 → 放弃
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_retries:
                        wait = backoff * (2 ** attempt)
                        time.sleep(wait)
            raise last_error
        return wrapper
    return decorator


def ok(data=None, **extra):
    """统一成功返回 {"success": true, "data": ...}"""
    result = {"success": True}
    if data is not None:
        result["data"] = data
    result.update(extra)
    return json.dumps(result, ensure_ascii=False)


def fail(error, help_msg=None, **extra):
    """统一失败返回 {"success": false, "error": "...", "help": "..."}"""
    result = {"success": False, "error": error}
    if help_msg:
        result["help"] = help_msg
    result.update(extra)
    return json.dumps(result, ensure_ascii=False)
