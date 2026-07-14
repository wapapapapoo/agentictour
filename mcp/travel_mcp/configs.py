import os
from pathlib import Path

from dotenv import load_dotenv

CURRENT_FILE = Path(__file__).resolve()
BASE_DIR = CURRENT_FILE.parents[1]
ENV_PATH = BASE_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)


class Settings:
    AMAP_KEY: str = os.getenv("AMAP_KEY", "")

    MCP_HOST: str = os.getenv("MCP_HOST", "0.0.0.0")
    MCP_PORT: int = int(os.getenv("MCP_PORT", "8001"))
    MCP_PATH: str = os.getenv("MCP_PATH", "/mcp")

    HTTP_TIMEOUT: int = int(os.getenv("HTTP_TIMEOUT", "10"))

    DIFY_KNOWLEDGE_URL: str = os.getenv(
        "DIFY_KNOWLEDGE_URL", "http://host.docker.internal:3000/v1"
    )
    DIFY_KNOWLEDGE_API_KEY: str = os.getenv("DIFY_KNOWLEDGE_API_KEY", "")

    AMAP_BASE_URL: str = "https://restapi.amap.com"


settings = Settings()


def check_settings() -> None:
    if not settings.AMAP_KEY:
        raise RuntimeError(
            "缺少 AMAP_KEY，请在 mcp/.env 中配置：AMAP_KEY=你的高德 Web 服务 Key"
        )