"""第十九课：pytest — 自动化测试

之前怎么验证代码没问题？
  手动跑一遍 → 眼睛看输出 → 判断对不对
  改了一处代码 → 全部重测一遍（累）

pytest 做的事：
  你把"什么是对"写成规则 → pytest 自动跑 → 自动告诉你哪过了哪炸了

类比：
  手动测试 = 人工质检，一个个检查
  pytest   = 安检门，人走过去自动响

三个核心概念：
  1. test 开头的函数 = 一个测试用例
  2. assert       = "我断言这个结果应该是 X"（不对就报错）
  3. pytest 命令   = 自动找到所有 test_ 函数，全部跑一遍
"""

# ═══════════════════════════════════════════════════════════
# 第一部分：最简单的例子
# ═══════════════════════════════════════════════════════════


def add(a, b):
    """加法函数"""
    return a + b


def test_add_normal():
    """正常情况：1+1=2"""
    assert add(1, 1) == 2


def test_add_zero():
    """加零不变"""
    assert add(5, 0) == 5


def test_add_negative():
    """负数也能加"""
    assert add(-1, -1) == -2


# ═══════════════════════════════════════════════════════════
# 第二部分：测试工具函数 utils.py
# ═══════════════════════════════════════════════════════════

import json

# 把 utils 里的函数复制过来（实际测试时会 import）
# 这里直接写，不用 import，方便理解 pytest 本身


def ok(data=None, **extra):
    """统一成功返回"""
    result = {"success": True}
    if data is not None:
        result["data"] = data
    result.update(extra)
    return json.dumps(result, ensure_ascii=False)


def fail(error, help_msg=None, **extra):
    """统一失败返回"""
    result = {"success": False, "error": error}
    if help_msg:
        result["help"] = help_msg
    result.update(extra)
    return json.dumps(result, ensure_ascii=False)


def test_ok_no_data():
    """ok() 不带参数，返回 success=true"""
    r = json.loads(ok())
    assert r["success"] is True
    assert "data" not in r


def test_ok_with_data():
    """ok() 带数据，返回 data 字段"""
    r = json.loads(ok({"name": "小光"}))
    assert r["success"] is True
    assert r["data"] == {"name": "小光"}


def test_ok_with_extra():
    """ok() 带额外字段"""
    r = json.loads(ok({"a": 1}, message="完成"))
    assert r["success"] is True
    assert r["data"] == {"a": 1}
    assert r["message"] == "完成"


def test_fail_basic():
    """fail() 基本用法"""
    r = json.loads(fail("网络超时"))
    assert r["success"] is False
    assert r["error"] == "网络超时"


def test_fail_with_help():
    """fail() 带帮助信息"""
    r = json.loads(fail("超时", help_msg="检查网络"))
    assert r["success"] is False
    assert r["error"] == "超时"
    assert r["help"] == "检查网络"


# ═══════════════════════════════════════════════════════════
# 第三部分：带"预期出错"的测试
# ═══════════════════════════════════════════════════════════

def test_add_type_error():
    """字符串+数字 应该报错"""
    try:
        add("hello", 5)
        assert False, "应该报错但没有报"  # 走到这里说明没报错，测试失败
    except TypeError:
        assert True  # 报错了，符合预期


# ═══════════════════════════════════════════════════════════
# 用法说明
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 50)
    print("  pytest 自动化测试 — 第 19 课")
    print("=" * 50)
    print()
    print("  📁 本文件同时包含测试用例（test_ 开头的函数）")
    print()
    print("  🏃 运行测试：")
    print("     source venv/bin/activate")
    print("     pytest 19_pytest_test.py -v")
    print()
    print("  👀 参数说明：")
    print("     -v    = verbose，显示每个测试的名字和结果")
    print("     -s    = 允许 print 输出（默认隐藏）")
    print("     -k    = 只跑名字匹配的测试（如 -k 'ok'）")
    print("     --lf  = 只跑上次失败的测试（--last-failed）")
    print()
    print("  输出示例：")
    print("     19_pytest_test.py::test_add_normal     PASSED")
    print("     19_pytest_test.py::test_add_zero       PASSED")
    print("     19_pytest_test.py::test_add_negative   PASSED")
    print("     ========== 3 passed in 0.05s ==========")
    print()
    print("  📝 规则：")
    print("     - 文件名必须以 test_ 开头或 _test 结尾")
    print("     - 函数名必须以 test_ 开头")
    print("     - 用 assert 判断对错，True 通过，False 失败")
    print("     - pytest 自动发现这些函数，不需要手动指定")
    print()
    print("  🧠 脑记：")
    print("     assert = 我断言 = 我说结果应该是这个")
    print("     写测试 = 把「什么是对的」提前写下来")
    print("     pytest = 自动裁判，一个一个验")
