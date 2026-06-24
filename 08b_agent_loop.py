"""08b：Agent 循环深入 — 看清每一步"AI决策→代码执行→结果回传"

类比：你在微信上让朋友帮你订外卖
  你：帮我订个附近好吃的披萨
  朋友(AI大脑)：我得先知道你地址 → 发消息问你(code帮你查)
  你(code返回)：你在朝阳区
  朋友(AI大脑)：好，朝阳区有哪些披萨店 → 查地图(code)
  地图(code返回)：3家店
  朋友(AI大脑)：评分最高的是XX → 帮你下单(code)
  外卖(code返回)：下单成功
  朋友：订好了！XX披萨30分钟到

每一轮 = AI动嘴说"我要这个" + 代码动手做 + 结果扔回给AI继续想
"""

import anthropic
import json

client = anthropic.Anthropic()

# ══════════════════════════════════════════════════════════════
# 工具定义 — 模拟一个生活助手的三个能力
# ══════════════════════════════════════════════════════════════

tools = [
    {
        "name": "get_user_city",
        "description": "获取当前用户所在城市",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_weather",
        "description": "获取指定城市的天气",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "城市名"}
            },
            "required": ["city"]
        }
    },
    {
        "name": "find_restaurants",
        "description": "搜索某城市某类餐厅",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "城市名"},
                "cuisine": {"type": "string", "description": "菜系，如川菜、日料"}
            },
            "required": ["city", "cuisine"]
        }
    }
]

# 工具的实际实现（代码动手的部分）
def get_user_city():
    return {"city": "北京"}

def get_weather(city):
    return {"city": city, "weather": "中雨", "temp": 22}

def find_restaurants(city, cuisine):
    data = {
        ("北京", "川菜"): [{"name": "川味轩", "rating": 4.8, "distance": "500m"}],
        ("北京", "日料"): [{"name": "樱花亭", "rating": 4.5, "distance": "800m"}],
        ("北京", "火锅"): [{"name": "火宴山", "rating": 4.6, "distance": "1.2km"}],
    }
    results = data.get((city, cuisine), [{"name": f"{city}{cuisine}推荐店", "rating": 4.0, "distance": "未知"}])
    return {"restaurants": results}

TOOLS_MAP = {
    "get_user_city": get_user_city,
    "get_weather": get_weather,
    "find_restaurants": find_restaurants,
}

# ══════════════════════════════════════════════════════════════
# 辅助函数 — 格式化打印，让每一步清晰可见
# ══════════════════════════════════════════════════════════════

round_num = [0]  # 用列表方便在函数里修改

def print_divider(label):
    """打印分隔线"""
    print()
    print("┌" + "─" * 58 + "┐")
    print(f"│  {label}")
    print("└" + "─" * 58 + "┘")

def handle_tool_calls(response, history):
    """处理 AI 返回的工具调用，可能一次返回多个工具调用"""
    texts = []
    tool_calls = []

    for block in response.content:
        if block.type == "text":
            texts.append(block.text)
        elif block.type == "tool_use":
            tool_calls.append(block)

    # 先输出 AI 的文字部分
    for t in texts:
        print(f"  💬 AI说：{t}")

    # 如果没有工具调用，把文字加入历史，返回
    if not tool_calls:
        if texts:
            history.append({"role": "assistant", "content": "".join(texts)})
        return "".join(texts), False

    # ═══ 有工具调用 ═══
    # Step A: 记录 AI 的 tool_use 到历史
    history.append({"role": "assistant", "content": [b for b in response.content if b.type == "tool_use"]})

    tool_results = []

    for tc in tool_calls:
        round_num[0] += 1
        rn = round_num[0]

        # Step B: 展示 AI 的决定
        print()
        print(f"  ╭── 第{rn}轮 · AI决策 ──")
        print(f"  │  🧠 AI决定调用：{tc.name}")
        print(f"  │  📋 参数：{json.dumps(tc.input, ensure_ascii=False)}")
        print(f"  │  💡 这句话翻译成人话：AI说「我需要{tc.name}这个信息」")
        print(f"  ╰──")

        # Step C: 代码执行
        func = TOOLS_MAP[tc.name]
        result = func(**tc.input)
        print(f"  ╭── 第{rn}轮 · 代码执行 ──")
        print(f"  │  ⚡ 代码动手跑了：{tc.name}(**{tc.input})")
        print(f"  │  📦 返回结果：{json.dumps(result, ensure_ascii=False)}")
        print(f"  │  💡 这就是「代码动手」——函数被真实调用，返回真实数据")
        print(f"  ╰──")

        tool_results.append({
            "tool_use_id": tc.id,
            "content": json.dumps(result, ensure_ascii=False)
        })

    # Step D: 把结果塞回对话（结果回传）
    history.append({
        "role": "user",
        "content": [{"type": "tool_result", **tr} for tr in tool_results]
    })

    print(f"  ╭── 结果回传 ──")
    print(f"  │  📤 把 {len(tool_results)} 个工具结果塞回对话历史")
    print(f"  │  💡 AI 拿到这些数据后会再次思考：够回答了吗？还需要调工具吗？")
    print(f"  ╰──")

    return "", True  # 表示"别停，继续问AI"


# ══════════════════════════════════════════════════════════════
# 主流程
# ══════════════════════════════════════════════════════════════

SYSTEM = """你是一个生活助手。用户想了解出行建议时，你需要：
1. 先获取用户城市
2. 再查天气
3. 如果天气不好（比如下雨），推荐附近餐厅，建议用户别跑太远
每次回答前先想清楚是否需要调工具。用热情口语回答。"""

print("=" * 60)
print("  Agent 循环演示 — 一次提问，多次工具调用")
print("=" * 60)
print()
print("  用户会问：今晚适合出门吃饭吗？")
print("  这个问题 AI 需要查三样信息：位置 → 天气 → 餐厅")
print("  你将看到 AI 一轮一轮地调用工具，直到信息够用")
print()

input("按回车开始演示...")

history = []
user_msg = "今晚适合出门吃饭吗？我想吃火锅"
history.append({"role": "user", "content": user_msg})

print_divider(f"用户提问：{user_msg}")

max_rounds = 10  # 防止死循环
for i in range(max_rounds):
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        thinking={"type": "disabled"},
        system=SYSTEM,
        tools=tools,
        messages=history,
    )

    reply, had_tools = handle_tool_calls(response, history)

    if not had_tools:
        # AI 给出了最终文字回答
        print()
        print_divider("✅ 最终回答（AI综合了所有工具结果后给出的）")
        print(f"  {reply}")
        break
else:
    print("⚠️ 达到最大轮次，可能死循环了")

print()
print("=" * 60)
print("  总结：你看到 AI 一轮轮调用工具的过程")
print("  每轮都是：AI说「我要X」→ 代码给X → AI想下一步")
print("  这就是 Agent 的核心循环 🔄")
print("=" * 60)
