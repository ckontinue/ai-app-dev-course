"""第十五课：SQLite 对话记录 → Pandas 分析 → matplotlib 可视化

Pandas 是什么？
  一个 Python 库，专做数据分析。读数据库、算平均值、分组统计，
  就像一个"用代码操控的 Excel"。

matplotlib 是什么？
  Python 的画图库，把数字变成柱状图、饼图、折线图、散点图。

本课流程：
  1. Pandas 从 SQLite 读取对话数据
  2. 统计用户/助手消息数量、平均长度、每日对话量
  3. matplotlib 画四张图，保存为 PNG
"""

import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# ═══════════════════════════════════════════════════════════
# 1. 用 Pandas 读取 SQLite 数据
# ═══════════════════════════════════════════════════════════
# pd.read_sql_query("SQL语句", 数据库连接) → 直接返回一个 DataFrame（就是表格）
conn = sqlite3.connect("conversations.db")
df = pd.read_sql_query("SELECT * FROM conversations ORDER BY id", conn)
conn.close()

# df.head() = 看一眼前几行
print("=" * 50)
print("📊 原始数据（前 5 行）：")
print(df.head())
print(f"\n共 {len(df)} 条记录\n")

# ═══════════════════════════════════════════════════════════
# 2. 计算统计指标
# ═══════════════════════════════════════════════════════════

# 2a. 用户 vs 助手消息数量
role_counts = df["role"].value_counts()
print("👥 角色分布：")
for role, count in role_counts.items():
    print(f"   {role}: {count} 条")

# 2b. 每条消息的长度
df["length"] = df["content"].str.len()
print(f"\n📏 消息长度统计：")
print(f"   平均长度：{df['length'].mean():.0f} 字符")
print(f"   最长消息：{df['length'].max()} 字符")
print(f"   最短消息：{df['length'].min()} 字符")

# 2c. 按角色看平均长度
print(f"\n📏 按角色平均长度：")
for role in df["role"].unique():
    avg_len = df[df["role"] == role]["length"].mean()
    print(f"   {role}: {avg_len:.0f} 字符")

# 2d. 时间分析（如果有时间戳的话）
if "created_at" in df.columns:
    # Pandas 的 to_datetime() = 把文字时间变成 Python 能理解的时间对象
    df["time"] = pd.to_datetime(df["created_at"])
    print(f"\n⏰ 时间跨度：")
    print(f"   最早：{df['time'].min()}")
    print(f"   最晚：{df['time'].max()}")

    # 按日期分组，数每天多少条
    df["date"] = df["time"].dt.date
    daily = df.groupby("date").size()
    print(f"\n📅 每日对话量：")
    for date, count in daily.items():
        bar = "█" * count
        print(f"   {date}: {bar} ({count}条)")

# ═══════════════════════════════════════════════════════════
# 3. matplotlib 画图
# ═══════════════════════════════════════════════════════════

# 中文字体（防止中文显示成方块）
plt.rcParams['font.sans-serif'] = ['DejaVu Sans']

# 创建 2x2 四张子图
fig, axes = plt.subplots(2, 2, figsize=(12, 10))
fig.suptitle("AI Chatbot Analytics Report", fontsize=16, fontweight="bold")

# --- 图1：角色分布饼图 ---
ax1 = axes[0, 0]
role_labels = role_counts.index.tolist()
role_values = role_counts.values.tolist()
colors = ['#ff9999', '#66b3ff']
ax1.pie(role_values, labels=role_labels, autopct='%1.1f%%', colors=colors, startangle=90)
ax1.set_title("User vs Assistant Messages")

# --- 图2：消息长度柱状图（按角色） ---
ax2 = axes[0, 1]
role_avg_len = [df[df["role"] == r]["length"].mean() for r in role_labels]
bars = ax2.bar(role_labels, role_avg_len, color=colors)
ax2.set_title("Avg Message Length by Role")
ax2.set_ylabel("Characters")
for bar, val in zip(bars, role_avg_len):
    ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
             f'{val:.0f}', ha='center', fontsize=11)

# --- 图3：每条消息长度折线图 ---
ax3 = axes[1, 0]
ax3.plot(range(len(df)), df["length"], marker='o', linestyle='-', color='#8888cc')
ax3.set_title("Message Length per Turn")
ax3.set_xlabel("Turn Number")
ax3.set_ylabel("Characters")

# --- 图4：每日对话柱状图 ---
ax4 = axes[1, 1]
if "date" in df.columns and len(daily) > 0:
    dates_str = [str(d) for d in daily.index]
    ax4.bar(dates_str, daily.values, color='#99cc99')
    ax4.set_title("Messages per Day")
    ax4.set_ylabel("Count")
    for i, v in enumerate(daily.values):
        ax4.text(i, v + 0.1, str(v), ha='center')
else:
    ax4.text(0.5, 0.5, 'All messages on same day', ha='center', va='center',
             transform=ax4.transAxes, fontsize=14, color='gray')
    ax4.set_title("Messages per Day")

plt.tight_layout()
plt.savefig("analytics_report.png", dpi=150)
print("\n✅ 图表已保存为 analytics_report.png")

# ═══════════════════════════════════════════════════════════
# 4. 额外：导出 CSV（Excel 也能打开）
# ═══════════════════════════════════════════════════════════
df[["id", "role", "content", "created_at"]].to_csv("conversations.csv", index=False, encoding="utf-8-sig")
print("✅ 数据已导出为 conversations.csv（可用 Excel 打开）")
