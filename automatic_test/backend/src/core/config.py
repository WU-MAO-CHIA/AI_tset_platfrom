from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./data/autotest.db"
    media_root: str = "./data/media"
    robot_scripts_dir: str = "./robot_scripts"
    parallel_max_workers: int = 5

    anthropic_api_key: str = ""
    openai_api_key: str = ""
    default_llm_model: str = "claude-3-5-sonnet-20241022"


@lru_cache
def get_settings() -> Settings:
    return Settings()
