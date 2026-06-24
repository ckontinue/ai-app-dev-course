# ── 基础镜像：Python 3.12 精简版 ──
FROM python:3.12-slim

# ── 工作目录（容器里的项目文件夹）──
WORKDIR /app

# ── 先复制依赖文件，再安装包 ——
# 为什么要分两步？先 COPY requirements 再 COPY 代码：
#   改了代码不会触发重新 pip install，利用 Docker 缓存加速构建
COPY requirements.txt .
RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --no-cache-dir -r requirements.txt

# ── 预下载 Chroma 向量模型（避免每次新容器等几分钟）──
RUN python3 -c "import chromadb; c=chromadb.Client(); c.create_collection('warmup'); c.delete_collection('warmup')"

# ── 复制源码（只复制需要的文件）──
COPY 18_fastapi_app.py .
COPY config.py .
COPY utils.py .
COPY logger.py .
COPY company_docs.txt .

# ── 声明端口（文档作用，不实际占用）──
EXPOSE 9988

# ── 启动命令 ──
CMD ["python3", "18_fastapi_app.py"]
