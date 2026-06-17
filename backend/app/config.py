import os
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres.cfczleeqgaytivtlbbhv:umtlmsaccount-786@aws-1-ap-northeast-2.pooler.supabase.com:6543/postgres",
    )
    secret_key: str = os.getenv("SECRET_KEY", "change-this-secret-key-in-production")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440")
    )
    cors_origins: str = os.getenv("CORS_ORIGINS", "*")

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
