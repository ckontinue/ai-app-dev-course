# AI 应用开发课程作品集

从零基础到容器化部署，19 节课逐步构建的 AI 应用开发项目。

## 技术栈

| 层级 | 技术 |
|------|------|
| AI 模型 | Claude API (via DeepSeek 中转) |
| 后端框架 | FastAPI + Uvicorn |
| 前端框架 | Gradio |
| 向量数据库 | ChromaDB |
| Agent 框架 | LangChain |
| 数据库 | SQLite |
| 容器化 | Docker + Docker Compose |
| 测试 | Pytest (38 个测试) |

## 项目结构

```
.
├── 01~04  入门基础      Hello World → 多轮对话 → 聊天机器人
├── 05~07  RAG 检索增强  知识库搜索 → 向量搜索 → AI 客服
├── 08~09  Agent 智能体   工具调用 → Agent 循环 → 多工具协同
├── 10~15  工程化应用     Web 应用 → 数据库 → 数据分析
├── 16~17  看板与报告     Gradio 仪表盘 → 对话总结
├── 18     后端 API      FastAPI REST 接口
├── 19     自动化测试    Pytest 单元测试
├── Dockerfile           容器化部署
├── docker-compose.yml   双容器编排
└── tests/               测试套件
```

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 设置环境变量
export ANTHROPIC_AUTH_TOKEN=your_key
export ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic

# 3. 启动 FastAPI 服务
python3 18_fastapi_app.py

# 4. 打开接口文档
# http://localhost:9988/docs
```

## Docker 部署

```bash
docker compose up -d
```

- FastAPI 后端: http://localhost:9988
- 看板前端: http://localhost:7860

## 学习路径

1. **基础调用** — 理解 API 请求、System Prompt、多轮对话
2. **RAG 检索增强** — 向量数据库、文档切片、语义搜索
3. **Agent 智能体** — 工具定义、自主决策、多工具编排
4. **工程化** — Web 框架、数据库持久化、REST API 设计
5. **容器化部署** — Dockerfile 编写、双容器编排、环境变量管理
