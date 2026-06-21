from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./data/autotest.db"
    media_root: str = "./data/media"
    robot_scripts_dir: str = "./robot_scripts"
    execution_reports_dir: str = "./data/execution_reports"
    parallel_max_workers: int = 5

    anthropic_api_key: str = ""
    openai_api_key: str = ""
    default_llm_model: str = "claude-sonnet-4-6"

    jwt_secret_key: str = "dev-secret-key-change-in-production"
    # 168h = 7 天，避免測試人員每天重新登入而觸發 token 過期 401
    jwt_expire_hours: int = 168
    admin_username: str = "admin"
    admin_password: str = "admin"


@lru_cache
def get_settings() -> Settings:
    return Settings()
