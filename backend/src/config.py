from abc import ABC
from functools import lru_cache
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class ConfigABC(BaseSettings, ABC):

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="allow",
    )


class Log(ConfigABC):

    level: Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"] = Field(
        alias="LOG_LEVEL",
        default="WARNING",
    )
    format: str = Field(
        alias="LOG_FORMAT",
        default="%(levelname)-10s%(asctime)-25s %(name)s - %(funcName)-15s: %(lineno)-5d - %(message)3s",
    )


class Settings(ConfigABC):
    log: Log = Log()


@lru_cache(1)
def get_settings() -> Settings:
    return Settings()
