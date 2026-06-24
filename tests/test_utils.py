"""测试 utils.py — 工具箱的三个函数"""

import json
import sys
import os

# 把上级目录加到搜索路径（因为 test 文件在 tests/ 子目录）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import ok, fail, retry


# ═══════════════════════════════════════════════════════════
# ok() 测试
# ═══════════════════════════════════════════════════════════

def test_ok_no_data():
    """ok() 不带参数 → success=true，没有 data 字段"""
    r = json.loads(ok())
    assert r["success"] is True
    assert "data" not in r


def test_ok_with_data():
    """ok(数据) → 返回里带 data"""
    r = json.loads(ok({"city": "Beijing"}))
    assert r["success"] is True
    assert r["data"] == {"city": "Beijing"}


def test_ok_extra_fields():
    """ok(data, message="完成") → 额外字段也带上"""
    r = json.loads(ok({"a": 1}, message="完成"))
    assert r["success"] is True
    assert r["data"] == {"a": 1}
    assert r["message"] == "完成"


def test_ok_chinese_data():
    """ok() 带中文数据，ensure_ascii=False 所以中文正常显示"""
    r = ok({"城市": "北京"})
    assert "北京" in r
    assert "\\u" not in r   # 不是 unicode 转义


# ═══════════════════════════════════════════════════════════
# fail() 测试
# ═══════════════════════════════════════════════════════════

def test_fail_basic():
    """fail('错误原因') → success=false，带 error"""
    r = json.loads(fail("网络超时"))
    assert r["success"] is False
    assert r["error"] == "网络超时"


def test_fail_with_help():
    """fail('错', help_msg='怎么修') → 带 help 字段"""
    r = json.loads(fail("超时", help_msg="检查网络"))
    assert r["success"] is False
    assert r["error"] == "超时"
    assert r["help"] == "检查网络"


def test_fail_without_help():
    """fail('错') → 没有 help 字段"""
    r = json.loads(fail("超时"))
    assert "help" not in r


def test_fail_extra_fields():
    """fail() 也支持额外字段"""
    r = json.loads(fail("失败", code=500))
    assert r["code"] == 500


# ═══════════════════════════════════════════════════════════
# retry() 测试 — 核心！
# ═══════════════════════════════════════════════════════════

def test_retry_success_first_try():
    """第一次就成功，不重试"""
    call_count = 0

    @retry(max_retries=3, backoff=0.01)
    def work():
        nonlocal call_count
        call_count += 1
        return "完成"

    result = work()
    assert result == "完成"
    assert call_count == 1   # 只调了一次，没重试


def test_retry_success_after_failure():
    """第 2 次才成功，重试了 1 次"""
    call_count = 0

    @retry(max_retries=3, backoff=0.01)
    def work():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ConnectionError("网络断了")
        return "终于成了"

    result = work()
    assert result == "终于成了"
    assert call_count == 2   # 第一次失败，第二次成功


def test_retry_all_failed():
    """重试用完还是失败 → 抛出最后的异常"""
    @retry(max_retries=2, backoff=0.01)
    def work():
        raise ValueError("每次都炸")

    try:
        work()
        assert False, "应该抛出异常"
    except ValueError as e:
        assert "每次都炸" in str(e)


def test_retry_preserves_function_name():
    """@retry 不应该盖掉函数名"""
    @retry(max_retries=1, backoff=0.01)
    def my_cool_function():
        return "ok"

    assert my_cool_function.__name__ == "my_cool_function"
