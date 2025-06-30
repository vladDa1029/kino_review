from abc import ABC
from functools import lru_cache
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class ConfigABC(BaseSettings, ABC):

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent.parent / ".env",
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


class Auth(ConfigABC):
    """
    Настройки для работы авторизационной системы.
    """

    access_token_time: int = Field(alias="ACCESS_TOKEN_TIME_SECONDS", default=600)
    refresh_token_time: int = Field(alias="REFRESH_TOKEN_TIME_SECONDS", default=3600)
    algoritm: str = Field(alias="AUTH_ALGORITM", default="RS256")

    @property
    def PRIVATE_KEY(self) -> str | None:
        with open(
            file=Path(__file__).resolve().parent.parent.parent
            / "src"
            / "auth"
            / "private_key.pem",
            mode="rb",
        ) as file:
            return file.read()

    @property
    def PUBLIC_KEY(self) -> str | None:
        with open(
            file=Path(__file__).resolve().parent.parent.parent
            / "src"
            / "auth"
            / "public_key.pem",
            mode="rb",
        ) as file:
            return file.read()


class DatabaseSettings(ConfigABC):
    """
    Настройки для подключения к базе данных.
    Здесь есть параметры Optional с той целью, потому что может использоваться sqlite(не может мне лень).
    """

    host: str | None = Field(alias="DATABASE_HOST", default=None)
    port: int | None = Field(alias="DATABASE_PORT_NETWORK", default=None)
    user: str | None = Field(alias="DATABASE_USER", default=None)
    password: str | None = Field(alias="DATABASE_PASSWORD", default=None)
    name: str = Field(alias="DATABASE_NAME")
    dialect: str = Field(alias="DATABASE_DIALECT")
    driver: str = Field(alias="DATABASE_DRIVER")

    @property
    def url(self) -> str:
        if self.dialect == "sqlite":
            return f"{self.dialect}+{self.driver}:///{self.name}"

        return f"{self.dialect}+{self.driver}://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class Settings(ConfigABC):
    log: Log = Log()
    db: DatabaseSettings = DatabaseSettings()
    auth: Auth = Auth()


@lru_cache(1)
def get_settings() -> Settings:
    return Settings()
