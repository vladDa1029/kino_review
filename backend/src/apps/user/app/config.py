from abc import ABC
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AmqpDsn, Field
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
        default="INFO",
    )
    format: str = Field(
        alias="LOG_FORMAT",
        default="%(levelname)-10s%(asctime)-25s %(name)s - %(funcName)-15s: %(lineno)-5d - %(message)3s",
    )
    logger_name: str = Field(
        alias="LOG_NAME",
        default="user",
    )


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


class DatabaseSettings(ConfigABC):
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

        return (
            f"{self.dialect}+{self.driver}://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}"
        )


class SQLAlchemySettings(ConfigABC):
    echo: bool = True
    echo_pool: bool = False
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 1800
    pool_pre_ping: bool = True

    auto_flush: bool = True
    expire_on_commit: bool = False


class StorageSettings(ConfigABC):
    backend: Literal["local", "s3", "minio"] = Field(
        alias="STORAGE_BACKEND",
        default="local",
    )
    bucket: str = Field(alias="STORAGE_BUCKET", default="user")
    local_root: Path = Field(alias="STORAGE_LOCAL_ROOT", default=Path("storage"))
    s3_endpoint_url: str | None = Field(alias="STORAGE_S3_ENDPOINT", default=None)
    s3_region: str | None = Field(alias="STORAGE_S3_REGION", default=None)
    s3_access_key: str | None = Field(alias="STORAGE_S3_ACCESS_KEY", default=None)
    s3_secret_key: str | None = Field(alias="STORAGE_S3_SECRET_KEY", default=None)
    s3_use_ssl: bool = Field(alias="STORAGE_S3_USE_SSL", default=True)


class ImageSettings(ConfigABC):
    allowed_mime_types: list[str] = Field(
        alias="IMAGE_ALLOWED_MIME_TYPES",
        default=["image/jpeg", "image/png", "image/webp"],
    )
    max_size_bytes: int = Field(
        alias="IMAGE_MAX_SIZE_BYTES",
        default=10 * 1024 * 1024,
    )


class ProjectService(ConfigABC):
    timeout_seconds: float = Field(alias="PROJECT_SERVICE_TIMEOUT_SECONDS", default=10.0)


class ConfirmationSettings(ConfigABC):
    secret_key: str = Field(
        alias="CONFIRMATION_SECRET_KEY",
        default="kino-confirmation-dev-key-please-change",
    )
    ttl_hours: int = Field(alias="CONFIRMATION_TTL_HOURS", default=24)
    public_base_url: str = Field(alias="PUBLIC_BASE_URL", default="http://localhost:8000")
    frontend_base_url: str = Field(
        alias="FRONTEND_BASE_URL",
        default="http://localhost:5173",
    )
    algorithm: str = Field(alias="CONFIRMATION_ALGORITHM", default="HS256")


class Settings(ConfigABC):
    log: Log = Log()
    db: DatabaseSettings = DatabaseSettings()
    alchemy: SQLAlchemySettings = SQLAlchemySettings()
    rabbitmq: Rabbitmq = Rabbitmq()
    storage: StorageSettings = StorageSettings()
    image: ImageSettings = ImageSettings()
    project_service: ProjectService = ProjectService()
    confirmation: ConfirmationSettings = ConfirmationSettings()


@lru_cache(1)
def get_settings() -> Settings:
    return Settings()
