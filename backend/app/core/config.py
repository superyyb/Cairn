"""应用配置 - 从 .env 加载环境变量"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # 数据库
    database_url: str

    # JWT
    secret_key: str
    access_token_expire_minutes: int = 10080
    algorithm: str = "HS256"
    
    # OpenAI(新增)
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # Google OAuth
    google_client_id: str = ""


settings = Settings()