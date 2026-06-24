"""第十六课：AI 对话数据可视化看板

把 15 课的静态图表升级成 Gradio 网页看板 ——
  自动刷新、能翻看、能搜索、能筛选日期。

看板上有什么：
  1. 总览数字卡片（总消息、活跃天数、平均轮数）
  2. 角色饼图
  3. 每日活跃柱状图
  4. 消息长度分布
  5. 对话搜索框
"""

import sqlite3
import os
import pandas as pd
import matplotlib.pyplot as plt
import gradio as gr
import requests
from datetime import datetime, timedelta
from collections import Counter
import re

DB_PATH = "conversations.db"

# ═══════════════════════════════════════════════════════════
# 1. 数据加载
# ═══════════════════════════════════════════════════════════
def load_data(days=30):
    """读取最近 N 天的对话数据"""
    conn = sqlite3.connect(DB_PATH)
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    df = pd.read_sql_query(
        "SELECT * FROM conversations WHERE created_at >= ? ORDER BY id",
        conn, params=(cutoff,)
    )
    conn.close()
    if df.empty:
        return df
    df["time"] = pd.to_datetime(df["created_at"])
    df["date"] = df["time"].dt.date
    df["length"] = df["content"].str.len()
    return df

# ═══════════════════════════════════════════════════════════
# 2. 总览数字
# ═══════════════════════════════════════════════════════════
def get_summary(df):
    if df.empty:
        return "暂无数据", "0 条", "0 天", "0 轮"
    total = len(df)
    active_days = df["date"].nunique()
    user_count = (df["role"] == "user").sum()
    return (
        f"📊 数据看板",
        f"{total} 条",
        f"{active_days} 天",
        f"{user_count} 轮",
    )

# ═══════════════════════════════════════════════════════════
# 3. 画图
# ═══════════════════════════════════════════════════════════
plt.rcParams['font.sans-serif'] = ['Source Han Sans SC', 'SimHei', 'WenQuanYi Micro Hei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False  # 防止负号显示成方块

def plot_pie(df):
    """角色分布饼图"""
    if df.empty:
        return None
    counts = df["role"].value_counts()
    fig, ax = plt.subplots(figsize=(5, 4))
    colors = ['#ff9999', '#66b3ff']
    labels = {"user": "用户提问", "assistant": "助手回复"}
    ax.pie(counts.values,
           labels=[labels.get(r, r) for r in counts.index],
           autopct='%1.1f%%', colors=colors[:len(counts)], startangle=90)
    ax.set_title("角色消息占比")
    return fig

def plot_daily_bars(df):
    """每日消息量柱状图"""
    if df.empty:
        return None
    daily = df.groupby("date").size().reset_index(name="count")
    daily["date"] = daily["date"].astype(str)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(range(len(daily)), daily["count"], color='#99cc99')
    # 只标几个刻度，免得挤
    step = max(1, len(daily) // 10)
    ticks = list(range(0, len(daily), step))
    ax.set_xticks(ticks)
    ax.set_xticklabels([daily.iloc[t]["date"] for t in ticks], rotation=45)
    ax.set_title("每日消息量")
    ax.set_ylabel("条数")
    return fig

def plot_length_hist(df):
    """消息长度分布直方图"""
    if df.empty:
        return None
    fig, ax = plt.subplots(figsize=(6, 4))
    user_lens = df[df["role"] == "user"]["length"]
    asst_lens = df[df["role"] == "assistant"]["length"]
    ax.hist(user_lens, bins=15, alpha=0.6, label="用户", color='#ff9999')
    ax.hist(asst_lens, bins=15, alpha=0.6, label="助手", color='#66b3ff')
    ax.set_title("消息长度分布")
    ax.set_xlabel("字符数")
    ax.set_ylabel("条数")
    ax.legend()
    return fig

def get_hot_words(df, top=15):
    """高频词统计（简单版：按字符切，统计2字以上词）"""
    if df.empty:
        return ""
    # 取用户消息
    user_msgs = df[df["role"] == "user"]["content"].str.cat(sep=" ")
    # 简单切词（中文按2-4字窗口滑动）
    words = []
    text = re.sub(r'[^一-鿿]', '', user_msgs)  # 只留中文
    for i in range(len(text) - 1):
        for wlen in [2, 3, 4]:
            if i + wlen <= len(text):
                words.append(text[i:i+wlen])
    # 过滤太短的
    counter = Counter(words)
    top_words = counter.most_common(top)
    if not top_words:
        return "*暂无足够中文数据*"
    lines = []
    for word, cnt in top_words:
        lines.append(f"- **{word}**：{cnt} 次")
    return "\n".join(lines)

# ═══════════════════════════════════════════════════════════
# 4. 对话搜索
# ═══════════════════════════════════════════════════════════
def search_history(query, days):
    """搜索历史对话"""
    if not query.strip():
        return "请输入搜索词"
    df = load_data(days)
    if df.empty:
        return "没有找到数据"
    mask = df["content"].str.contains(query, case=False, na=False)
    results = df[mask][["role", "content", "created_at"]]
    if results.empty:
        return f"没找到包含「{query}」的对话"
    lines = []
    for _, row in results.iterrows():
        role_label = "🧑 你" if row["role"] == "user" else "🤖 小光"
        preview = row["content"][:100].replace('\n', ' ')
        lines.append(f"**[{row['created_at']}]** {role_label}：{preview}...")
    return "\n\n---\n\n".join(lines[:20])  # 最多显示20条

# ═══════════════════════════════════════════════════════════
# 5. AI 助手 — 调 FastAPI 接口
# ═══════════════════════════════════════════════════════════
# 容器里 localhost 指向自己，所以 API 地址要允许外部设
API_HOST = os.environ.get("API_HOST", "localhost")
API_PORT = os.environ.get("API_PORT", "9988")
API_URL = f"http://{API_HOST}:{API_PORT}/chat"


def ask_ai(message, history):
    """把用户问题发给 FastAPI，拿回 AI 回复"""
    if not message.strip():
        return "请输入问题"

    try:
        resp = requests.post(
            API_URL,
            json={"message": message, "history": history},
            timeout=60,
        )
        if resp.status_code == 200:
            data = resp.json()
            reply = data["reply"]
            sid = data["session_id"]
            # 把当前问答追加到历史
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": reply})
            return reply, history
        else:
            return f"❌ API 错误 ({resp.status_code}): {resp.text}", history
    except requests.exceptions.ConnectionError:
        return (
            "❌ 连不上 AI 服务，请确认 FastAPI 已在端口 "
            f"{os.environ.get('API_PORT', '9988')} 启动"
        ), history
    except Exception as e:
        return f"❌ 调用失败: {e}", history


# ═══════════════════════════════════════════════════════════
# 6. Gradio 界面
# ═══════════════════════════════════════════════════════════
def refresh_dashboard(days):
    df = load_data(days)
    summary = get_summary(df)
    return (
        summary[0], summary[1], summary[2], summary[3],
        plot_pie(df),
        plot_daily_bars(df),
        plot_length_hist(df),
        get_hot_words(df),
    )

# ═══════════════════════════════════════════════════════════
# 6. Gradio 界面
# ═══════════════════════════════════════════════════════════
with gr.Blocks(title="AI 对话分析看板") as demo:
    gr.Markdown("# 📊 AI 对话数据分析看板")
    gr.Markdown("SQLite → Pandas → Matplotlib → Gradio 自动化看板")

    # 控制栏
    with gr.Row():
        days_slider = gr.Slider(1, 90, value=30, step=1, label="📅 查看最近 N 天数据")
        refresh_btn = gr.Button("🔄 刷新看板", variant="primary")

    # 总览卡片
    gr.Markdown("## 📋 总览")
    with gr.Row():
        title_box = gr.Textbox(label="", value="📊 数据看板", interactive=False)
        total_box = gr.Textbox(label="总消息数", value="...", interactive=False)
        days_box = gr.Textbox(label="活跃天数", value="...", interactive=False)
        turns_box = gr.Textbox(label="对话轮数", value="...", interactive=False)

    # 图表区
    gr.Markdown("## 📈 统计图表")
    with gr.Row():
        pie_plot = gr.Plot(label="角色占比")
        length_plot = gr.Plot(label="消息长度分布")
    daily_plot = gr.Plot(label="每日消息量")

    # 高频词
    gr.Markdown("## ☁️ 高频话题词")
    hot_words = gr.Markdown("点击刷新加载数据")

    # 对话搜索
    gr.Markdown("## 🔍 搜索对话")
    with gr.Row():
        search_box = gr.Textbox(placeholder="输入关键词...", label="搜索词", scale=3)
        search_days = gr.Slider(1, 90, value=30, step=1, label="范围（天）", scale=1)
        search_btn = gr.Button("搜索", variant="secondary", scale=1)
    search_result = gr.Markdown("输入关键词后点击搜索")

    # ── AI 助手 ──
    gr.Markdown("## 🤖 AI 助手（调 FastAPI）")
    gr.Markdown(f"后端地址：`{API_URL}`")
    with gr.Row():
        ai_input = gr.Textbox(placeholder="想问小光什么？比如：帮我把「你好」翻译成英文", label="你的问题", scale=4)
        ai_btn = gr.Button("🤖 问 AI", variant="primary", scale=1)
    with gr.Row():
        ai_reply = gr.Markdown("点「问 AI」获取回复")
    ai_state = gr.State([])  # 存对话历史，藏在页面里不显示

    # 绑定事件
    refresh_btn.click(
        fn=refresh_dashboard,
        inputs=[days_slider],
        outputs=[title_box, total_box, days_box, turns_box, pie_plot, daily_plot, length_plot, hot_words],
    )
    search_btn.click(
        fn=search_history,
        inputs=[search_box, search_days],
        outputs=[search_result],
    )
    ai_btn.click(
        fn=ask_ai,
        inputs=[ai_input, ai_state],
        outputs=[ai_reply, ai_state],
    )
    # 页面加载时自动刷新一次
    demo.load(
        fn=refresh_dashboard,
        inputs=[days_slider],
        outputs=[title_box, total_box, days_box, turns_box, pie_plot, daily_plot, length_plot, hot_words],
    )

if __name__ == "__main__":
    import os
    port = int(os.environ.get("GRADIO_PORT", 7860))
    demo.launch(server_name="0.0.0.0", server_port=port, share=False, theme=gr.themes.Soft())
    print(f"\n📍 看板地址：http://localhost:{port}")
