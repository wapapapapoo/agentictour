# ============ 阶段 1: CI 检查 ============
FROM python:3.12-slim AS ci

WORKDIR /app

# 安装全部依赖（运行时 + 开发工具）
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

# 复制源码
COPY . .

# CI 检查：任何一步挂了，docker build 直接失败
RUN ruff check .
RUN mypy main.py
RUN pytest -v

# ============ 阶段 2: 运行 ============
FROM python:3.12-slim

WORKDIR /app

# 只装运行时依赖，镜像干净
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
