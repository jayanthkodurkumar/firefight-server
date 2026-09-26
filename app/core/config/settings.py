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


@lru_cache
def get_settings() -> Settings:
    return Settings()
