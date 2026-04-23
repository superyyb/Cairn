"""应用配置 - 从 .env 加载环境变量"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # database
    database_url: str

    # JWT
    secret_key: str
    access_token_expire_minutes: int = 10080  # 7 days
    algorithm: str = "HS256"  # JWT signature algo


# 全局单例
settings = Settings()