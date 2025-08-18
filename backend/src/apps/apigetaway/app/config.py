from functools import lru_cache
from typing import Annotated
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class BaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="allow",
    )


class Services(BaseSettings):
    auth: str = Field(alias="AUTH_URL", default="auth:8001")
    user: str = Field(alias="USER_URL", default="user:8002")
    project: str = Field(alias="PROJECT_URL", default="project:8003")


class Config(BaseSettings):
    services: Services = Services()


@lru_cache(1)
def get_settings() -> Config:
    return Config()
