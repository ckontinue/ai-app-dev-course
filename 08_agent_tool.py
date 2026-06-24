"""第八课：Agent — 让 AI 调用函数动手干活"""

import anthropic
import json

client = anthropic.Anthropic()

# ---- 1. 定义可调用的工具 ----
tools = [
    {
        "name": "get_weather",
        "description": "获取指定城市的天气",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "城市名，如 北京"}
            },
            "required": ["city"]
        }
    },
    {
        "name": "calculator",
        "description": "数学计算",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "算式，如 2+3*4"}
            },
            "required": ["expression"]
        }
    }
]

# ---- 2. 工具的实际实现 ----
def get_weather(city):
    return {"city": city, "weather": "晴天", "temp": 28}

def calculator(expression):
    return {"result": eval(expression)}  # 仅演示，别在生产环境用 eval

TOOL_IMPL = {"get_weather": get_weather, "calculator": calculator}

# ---- 3. 对话 ----
history = []

while True:
    user = input("\n你：")
    if user == "/quit":
        break

    history.append({"role": "user", "content": user})

    # 发送请求，告诉 AI 有哪些工具可用
    r = client.messages.create(
        model="claude-sonnet-4-6", max_tokens=300, thinking={"type": "disabled"},
        system="你是一个助手，可以调用工具获取信息。需要实时数据时调用工具。",
        tools=tools,        # ← 工具列表
        messages=history
    )

    # 4. 处理回复：看 AI 是想直接说话还是调用工具
    reply = ""
    for block in r.content:
        if block.type == "text":
            reply += block.text
        elif block.type == "tool_use":
            # AI 要调工具！执行它，把结果塞回对话
            name = block.name
            args = block.input
            print(f"  [调用工具: {name}({args})]")

            result = TOOL_IMPL[name](**args)

            # 把工具调用和结果都加入历史
            history.append({"role": "assistant", "content": [block]})
            history.append({
                "role": "user",
                "content": [{"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result, ensure_ascii=False)}]
            })

            # 再次请求 AI，让它在工具结果基础上生成最终回复
            r2 = client.messages.create(
                model="claude-sonnet-4-6", max_tokens=300, thinking={"type": "disabled"},
                system="你是一个助手，根据工具返回结果回答用户问题。",
                tools=tools,
                messages=history
            )
            for b2 in r2.content:
                if b2.type == "text":
                    reply += b2.text
                    history.append({"role": "assistant", "content": b2.text})

    if reply:
        print(f"AI：{reply}")
