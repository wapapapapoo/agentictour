# CI
FROM python:3.12-slim AS ci

WORKDIR /app

# dependency
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

# 复制源码
COPY . .

# run test
RUN ruff check .
RUN mypy main.py
RUN pytest -v

# CD
FROM python:3.12-slim

WORKDIR /app

# run
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
