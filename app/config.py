from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

# Load local .env for scripts; process/container variables still take precedence.
load_dotenv()

APP_ROOT = Path(__file__).resolve().parents[1]

def csv_env(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]

class Settings:
    app_name: str = os.getenv("APP_NAME", "Investigation Copilot API")
    app_env: str = os.getenv("APP_ENV", "development")
    api_v1_prefix: str = os.getenv("API_V1_PREFIX", "/api/v1")
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{(APP_ROOT / 'data' / 'investigation_copilot.db').as_posix()}")
    api_access_key: str = os.getenv("API_ACCESS_KEY", "")
    cors_origins: list[str] = csv_env("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    groq_base_url: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "25"))
    auto_create_db: bool = os.getenv("AUTO_CREATE_DB", "false" if os.getenv("APP_ENV", "development") == "production" else "true").lower() == "true"

settings = Settings()
