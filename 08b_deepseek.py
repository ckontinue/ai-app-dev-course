"""08b：Agent 改 DeepSeek 版 — 只改 4 处配置，Agent 逻辑不动"""

from openai import OpenAI
import json, os

# ❶ SDK 和客户端（改）
client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN", ""),
    base_url="https://api.deepseek.com"
)

# ❷ 工具定义格式（改）
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定城市的天气",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string", "description": "城市名，如 北京"}},
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "数学计算",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string", "description": "算式，如 2+3*4"}},
                "required": ["expression"]
            }
        }
    }
]

# 工具实现（不改）
def get_weather(city):
    return {"city": city, "weather": "晴天", "temp": 28}

def calculator(expression):
    return {"result": eval(expression)}

TOOL_IMPL = {"get_weather": get_weather, "calculator": calculator}

# ❸ system 放 messages 第一条（改）
SYSTEM = "你是一个助手，可以调用工具获取信息。需要实时数据时调用工具。"
history = [{"role": "system", "content": SYSTEM}]

print("Agent DeepSeek 版（/quit 退出）\n")

while True:
    user = input("你：")
    if user == "/quit":
        break

    history.append({"role": "user", "content": user})

    # ❹ API 调用方式（改）
    r = client.chat.completions.create(
        model="deepseek-chat",
        messages=history,
        tools=tools
    )

    msg = r.choices[0].message
    reply = ""

    if msg.content:
        reply = msg.content

    if msg.tool_calls:
        for tc in msg.tool_calls:
            name = tc.function.name
            args = json.loads(tc.function.arguments)
            print(f"  [调用工具: {name}({args})]")

            result = TOOL_IMPL[name](**args)

            # 工具调用和结果放入历史（格式改了）
            history.append(msg.model_dump())
            history.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result, ensure_ascii=False)
            })

        # 二次请求拿最终回复
        r2 = client.chat.completions.create(
            model="deepseek-chat",
            messages=history,
            tools=tools
        )
        reply = r2.choices[0].message.content
        history.append({"role": "assistant", "content": reply})

    if reply:
        print(f"AI：{reply}\n")
