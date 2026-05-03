"""全局配置：从 .env 读取，业务代码统一通过 `settings` 单例访问。"""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_env: str = "dev"
    app_port: int = 8000
    secret_key: str = "change-me"
    jwt_secret: str = "change-me"
    admin_username: str = "admin"
    admin_password: str = "admin123"

    # Database
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "zhiyou"
    postgres_password: str = "zhiyou_pwd"
    postgres_db: str = "zhiyou"

    redis_url: str = "redis://localhost:6379/0"

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "neo4j_pwd"

    # Dify
    dify_base_url: str = "http://localhost:5001/v1"
    dify_api_key: str = ""
    # 知识库 dataset id（在 Dify 后台「知识库」详情 URL 中可见）；填写后 /admin/knowledge/upload 会同步入库
    dify_dataset_id: str = ""
    dify_dataset_api_key: str = ""

    # ASR / TTS / Avatar
    asr_base_url: str = "http://localhost:10095"
    tts_base_url: str = "http://localhost:8001"
    tts_default_voice: str = "guide_female_01"
    # TTS 二级降级：edge | fish | none
    tts_secondary_provider: str = "none"
    fish_api_key: str = ""
    fish_voice_id: str = ""

    # LLM (sentiment / suggestion / KG extraction)
    llm_provider: str = "deepseek"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"
    dashscope_api_key: str = ""
    dashscope_model: str = "qwen-plus"

    cors_origins: str = "http://localhost:5173,http://localhost:5174,http://localhost:5175"

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
