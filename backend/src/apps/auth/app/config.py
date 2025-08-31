from abc import ABC
from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional, Self
from pydantic import Field, PrivateAttr, model_validator, AmqpDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


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


class Rebbitmq(ConfigABC):
    host: str = Field(
        alias="RABBITMQ_HOST",
        description="RabbitMQ host name or IP address.",
    )
    port: int = Field(
        alias="RABBITMQ_PORT",
        description="RabbitMQ server port.",
    )
    login: str = Field(
        alias="RABBITMQ_DEFAULT_USER",
        description="Default RabbitMQ username.",
    )
    password: str = Field(
        alias="RABBITMQ_DEFAULT_PASS",
        description="Default RabbitMQ password.",
    )

    @property
    def url(self):
        return str(
            AmqpDsn.build(
                scheme="amqp",
                username=self.login,
                password=self.password,
                host=self.host,
                port=self.port,
            )
        )


class Auth(ConfigABC):
    """
    Настройки для работы авторизационной системы.
    """

    access_token_time: int = Field(alias="ACCESS_TOKEN_TIME_SECONDS", default=600)
    refresh_token_time: int = Field(alias="REFRESH_TOKEN_TIME_SECONDS", default=3600)
    algoritm: str = Field(alias="AUTH_ALGORITM", default="RS256")

    # Приватные атрибуты для ключей
    _private_key: Optional[bytes] = PrivateAttr(default=None)
    _public_key: Optional[bytes] = PrivateAttr(default=None)

    @model_validator(mode="after")
    def load_keys_and_validate(self) -> Self:
        """Валидация + загрузка ключей в одном методе (Pydantic v2.4)"""
        # 1. Валидация логики токенов
        if self.access_token_time <= 0:
            raise ValueError("ACCESS_TOKEN_TIME_SECONDS должен быть > 0")
        if self.refresh_token_time <= self.access_token_time:
            raise ValueError(
                "REFRESH_TOKEN_TIME_SECONDS должен быть ДОЛЬШЕ access токена"
            )

        # 2. Загрузка ключей
        key_dir = Path(__file__).resolve().parent.parent / "app" / "key"

        try:
            self._private_key = (key_dir / "private_key.pem").read_bytes()
            self._public_key = (key_dir / "public_key.pem").read_bytes()
        except FileNotFoundError as e:
            raise RuntimeError(
                f"Ключи не найдены: {e}. Убедитесь, что запустили generate_keys.sh"
            ) from None

        return self

    @property
    def PRIVATE_KEY(self) -> bytes:
        if self._private_key is None:
            raise RuntimeError("PRIVATE_KEY не загружен! Вызовите load_keys()")
        return self._private_key

    @property
    def PUBLIC_KEY(self) -> bytes:
        if self._public_key is None:
            raise RuntimeError("PUBLIC_KEY не загружен! Вызовите load_keys()")
        return self._public_key


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


class SQLAlchemySettings(ConfigABC):
    # Параметры подключения
    echo: bool = True
    echo_pool: bool = False
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 1800
    pool_pre_ping: bool = True

    # Параметры поведения SQLAlchemy
    auto_flush: bool = True
    expire_on_commit: bool = False


class Settings(ConfigABC):
    log: Log = Log()
    db: DatabaseSettings = DatabaseSettings()
    auth: Auth = Auth()
    alchemy: SQLAlchemySettings = SQLAlchemySettings()


@lru_cache(1)
def get_settings() -> Settings:
    return Settings()
