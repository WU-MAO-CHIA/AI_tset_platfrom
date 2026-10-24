from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET = "dev-secret-key-change-in-production"
DEFAULT_ADMIN_PASSWORD = "admin"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "dev"  # dev | prod (prod 啟用嚴格啟動檢查)

    database_url: str = "sqlite+aiosqlite:///./data/autotest.db"
    media_root: str = "./data/media"
    robot_scripts_dir: str = "./robot_scripts"
    execution_reports_dir: str = "./data/execution_reports"
    parallel_max_workers: int = 5
    # 同時執行幾筆執行（清單或試跑，各自是一個 robot / pabot 子程序）；仍只有一個 uvicorn 行程
    execution_max_concurrent: int = 1

    anthropic_api_key: str = ""
    openai_api_key: str = ""
    default_llm_model: str = "claude-sonnet-4-6"
    # 本地 Ollama 原生 API base URL（空字串＝未啟用本地模型）
    ollama_base_url: str = ""

    jwt_secret_key: str = "dev-secret-key-change-in-production"
    # 閒置逾時（分鐘）：每次通過驗證的請求都會換發新 token，閒置超過此時間才需重新登入
    jwt_expire_minutes: int = 10080
    admin_username: str = "admin"
    admin_password: str = "admin"

    @field_validator("jwt_secret_key")
    @classmethod
    def _validate_secret(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters")
        return v

    @field_validator("app_env")
    @classmethod
    def _validate_env(cls, v: str) -> str:
        if v not in ("dev", "prod", "test"):
            raise ValueError("APP_ENV must be one of dev/prod/test")
        return v

    def is_default_secret(self) -> bool:
        return self.jwt_secret_key == DEFAULT_JWT_SECRET

    def is_default_admin_password(self) -> bool:
        return self.admin_password == DEFAULT_ADMIN_PASSWORD


@lru_cache
def get_settings() -> Settings:
    return Settings()
