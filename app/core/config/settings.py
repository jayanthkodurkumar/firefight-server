from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str
    telemetry_queue_url: str | None = None
    aws_region: str = "us-east-2"
    sqs_wait_time_seconds: int = 20
    sqs_max_messages: int = 10
    # Comma-separated origins, e.g. http://localhost:5173,http://127.0.0.1:3000
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"

    # Chat / LangGraph QA agent (OpenAI-compatible via init_chat_model)
    openai_api_key: str | None = None
    chat_model: str = "openai:gpt-4o-mini"

    jwt_secret_key: str = "dev-only-set-JWT_SECRET_KEY-in-env"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24
    password_reset_expire_hours: int = 1
    # Dev: return reset token in forgot-password JSON (disable when email is wired)
    auth_expose_reset_token: bool = True

    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
