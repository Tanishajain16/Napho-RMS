from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    DATABASE_URL: str = "sqlite:///./napho.db"
    SECRET_KEY: str = "change-me-in-production-use-32-char-min"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 10_485_760  # 10 MB
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    ANTHROPIC_API_KEY: str = ""


settings = Settings()
