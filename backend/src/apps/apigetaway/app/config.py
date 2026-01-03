from functools import lru_cache
from typing import Self
from pydantic import Field, PrivateAttr, model_validator
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


class ProtectedPathsSettings(BaseSettings):
    patterns: dict[str, list[str]] = Field(
        alias="PROTECTED_PATH_PATTERNS",
        default_factory=dict,
    )


class AuthGatewaySettings(BaseSettings):
    algorithm: str = Field(alias="AUTH_ALGORITHM", default="RS256")
    public_key_path: Path = Field(
        alias="AUTH_PUBLIC_KEY_PATH",
        default=Path(__file__).resolve().parent / "key" / "public_key.pem",
    )
    user_id_claim: str = Field(alias="AUTH_USER_ID_CLAIM", default="sub")
    token_type_claim: str = Field(alias="AUTH_TOKEN_TYPE_CLAIM", default="type")

    _public_key: bytes | None = PrivateAttr(default=None)

    @model_validator(mode="after")
    def load_public_key(self) -> Self:
        self._public_key = self.public_key_path.read_bytes()
        return self

    @property
    def public_key(self) -> bytes:
        if self._public_key is None:
            raise RuntimeError("AUTH public key is not loaded")
        return self._public_key


class Config(BaseSettings):
    services: Services = Services()
    auth_gateway: AuthGatewaySettings = AuthGatewaySettings()
    protected_paths: ProtectedPathsSettings = ProtectedPathsSettings()


@lru_cache(1)
def get_settings() -> Config:
    return Config()
