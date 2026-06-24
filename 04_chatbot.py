"""第四课：交互式聊天机器人 — 在终端里一直聊下去"""

import anthropic

client = anthropic.Anthropic()

# 角色设定
SYSTEM = "你是销售培训教练，回复简短有力，每次帮学员拆解一个销售话术要点。50字以内。"

# 记忆篮子
history = []

print("🤖 销售教练已上线（输入 /quit 退出）\n")

while True:
    user_input = input("你：")
    if user_input == "/quit":
        print("教练已下线。")
        break

    history.append({"role": "user", "content": user_input})

    r = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=150,
        thinking={"type": "disabled"},
        system=SYSTEM,
        messages=history
    )

    reply = None
    for b in r.content:
        if b.type == "text":
            reply = b.text
            print(f"教练：{reply}\n")

    history.append({"role": "assistant", "content": reply})
