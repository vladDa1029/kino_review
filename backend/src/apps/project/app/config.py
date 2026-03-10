from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AmqpDsn, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigABC(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="allow",
    )


class Log(ConfigABC):
    level: Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"] = Field(
        alias="LOG_LEVEL",
        default="INFO",
    )
    third_party_level: Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"] = Field(
        alias="LOG_THIRD_PARTY_LEVEL",
        default="WARNING",
    )
    format: str = Field(
        alias="LOG_FORMAT",
        default="%(levelname)-10s%(asctime)-25s %(name)s - %(funcName)-15s: %(lineno)-5d - %(message)3s",
    )
    logger_name: str = Field(
        alias="LOG_NAME",
        default="project",
    )


class DatabaseSettings(ConfigABC):
    host: str | None = Field(alias="DATABASE_HOST", default=None)
    port: int | None = Field(alias="DATABASE_PORT_NETWORK", default=None)
    user: str | None = Field(alias="DATABASE_USER", default=None)
    password: str | None = Field(alias="DATABASE_PASSWORD", default=None)
    name: str = Field(alias="DATABASE_NAME", default="kino-project")
    dialect: str = Field(alias="DATABASE_DIALECT", default="postgresql")
    driver: str = Field(alias="DATABASE_DRIVER", default="asyncpg")

    @model_validator(mode="after")
    def validate_required_network_fields(self) -> "DatabaseSettings":
        if self.dialect == "sqlite":
            return self
        missing = []
        if self.host is None:
            missing.append("DATABASE_HOST")
        if self.port is None:
            missing.append("DATABASE_PORT_NETWORK")
        if self.user is None:
            missing.append("DATABASE_USER")
        if self.password is None:
            missing.append("DATABASE_PASSWORD")
        if missing:
            raise ValueError("Missing required DB settings for non-sqlite: " + ", ".join(missing))
        return self

    @property
    def url(self) -> str:
        if self.dialect == "sqlite":
            return f"{self.dialect}+{self.driver}:///{self.name}"

        return (
            f"{self.dialect}+{self.driver}://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}"
        )


class SQLAlchemySettings(ConfigABC):
    echo: bool = False
    echo_pool: bool = False
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 1800
    pool_pre_ping: bool = True

    auto_flush: bool = True
    expire_on_commit: bool = False


class Rabbitmq(ConfigABC):
    host: str = Field(alias="RABBITMQ_HOST")
    port: int = Field(alias="RABBITMQ_PORT")
    login: str = Field(alias="RABBITMQ_DEFAULT_USER")
    password: str = Field(alias="RABBITMQ_DEFAULT_PASS")

    @property
    def url(self) -> str:
        return str(
            AmqpDsn.build(
                scheme="amqp",
                username=self.login,
                password=self.password,
                host=self.host,
                port=self.port,
            )
        )


class UserService(ConfigABC):
    base_url: str = Field(alias="USER_SERVICE_BASE_URL")
    timeout_seconds: float = Field(alias="USER_SERVICE_TIMEOUT_SECONDS", default=10.0)


class ReservationOutbox(ConfigABC):
    poll_interval_seconds: float = Field(
        alias="RESERVATION_OUTBOX_POLL_INTERVAL_SECONDS",
        default=5.0,
    )


class Minio(ConfigABC):
    endpoint_url: str = Field(alias="MINIO_ENDPOINT_URL")
    region_name: str = Field(alias="MINIO_REGION", default="us-east-1")
    access_key: str = Field(alias="MINIO_ACCESS_KEY")
    secret_key: str = Field(alias="MINIO_SECRET_KEY")
    bucket: str = Field(alias="MINIO_BUCKET", default="project-documents")
    secure: bool = Field(alias="MINIO_SECURE", default=False)
    presign_expires_seconds: int = Field(alias="MINIO_PRESIGN_EXPIRES_SECONDS", default=900)


class Settings(ConfigABC):
    log: Log = Log()
    db: DatabaseSettings = DatabaseSettings()
    alchemy: SQLAlchemySettings = SQLAlchemySettings()
    rabbitmq: Rabbitmq = Rabbitmq()
    user_service: UserService = UserService()
    reservation_outbox: ReservationOutbox = ReservationOutbox()
    minio: Minio = Minio()


@lru_cache(1)
def get_settings() -> Settings:
    return Settings()
