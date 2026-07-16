FROM node:22-bookworm-slim AS train-mcp

# Official package and pinned release from https://github.com/Joooook/12306-mcp
RUN npm install --global 12306-mcp@0.3.9

FROM python:3.12-slim-bookworm

COPY --from=train-mcp /usr/local/ /usr/local/

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8001
CMD ["sh", "-c", "12306-mcp --host 127.0.0.1 --port 8080 & exec python -m travel_mcp.server"]
