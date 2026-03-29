from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AmqpDsn, Field
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
    logger_name: str = Field(alias="LOG_NAME", default="notificate")


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


class SMTP(ConfigABC):
    host: str = Field(alias="SMTP_HOST", default="mailhog")
    port: int = Field(alias="SMTP_PORT", default=1025)
    username: str | None = Field(alias="SMTP_USERNAME", default=None)
    password: str | None = Field(alias="SMTP_PASSWORD", default=None)
    from_email: str = Field(alias="SMTP_FROM_EMAIL", default="no-reply@kino.local")
    from_name: str = Field(alias="SMTP_FROM_NAME", default="Kino")
    use_tls: bool = Field(alias="SMTP_USE_TLS", default=False)
    starttls: bool = Field(alias="SMTP_STARTTLS", default=False)
    timeout_seconds: float = Field(alias="SMTP_TIMEOUT_SECONDS", default=10.0)


class TaskIQ(ConfigABC):
    default_retry_count: int = Field(alias="TASKIQ_DEFAULT_RETRY_COUNT", default=3)
    default_delay_seconds: float = Field(alias="TASKIQ_DEFAULT_RETRY_DELAY_SECONDS", default=5.0)
    use_jitter: bool = Field(alias="TASKIQ_USE_JITTER", default=True)
    use_delay_exponent: bool = Field(alias="TASKIQ_USE_DELAY_EXPONENT", default=True)
    max_delay_exponent: float = Field(alias="TASKIQ_MAX_DELAY_EXPONENT", default=60.0)


class Settings(ConfigABC):
    log: Log = Log()
    rabbitmq: Rabbitmq = Rabbitmq()
    smtp: SMTP = SMTP()
    taskiq: TaskIQ = TaskIQ()


@lru_cache(1)
def get_settings() -> Settings:
    return Settings()
