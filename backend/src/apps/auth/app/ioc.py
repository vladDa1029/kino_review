from typing import Iterable
from dishka import Provider, Scope
from sqlalchemy.ext.asyncio import AsyncSession
from faststream.rabbit import RabbitBroker

from app.application.use_case.authenticate_uc import JWTAuthServices
from app.config import Auth, DatabaseSettings, Log, SQLAlchemySettings
from app.application.ports.transaction import TransactionManager
from app.infrastructure.adapters.repository import (
    UserAbstractRepository,
    UserSqlAlchemyRepository,
)
from app.infrastructure.database import get_engine, get_session, get_sessionmaker
from app.infrastructure.generation import AbstractGenerationID, GenerationUUID
from app.infrastructure.security.jwt import JWTServices
from app.infrastructure.security.password_hasher import PasswordHasher
from app.infrastructure.transactions import TransactionManagerAlchemy


def settings_provider() -> Provider:
    provider = Provider(scope=Scope.APP)
    provider.from_context(provides=Log)
    provider.from_context(provides=Auth)
    provider.from_context(provides=DatabaseSettings)
    provider.from_context(provides=SQLAlchemySettings)
    return provider


def db_provider() -> Provider:
    provider = Provider(scope=Scope.REQUEST)
    provider.provide(get_engine, scope=Scope.APP)
    provider.provide(get_sessionmaker, scope=Scope.APP)
    provider.provide(get_session, provides=AsyncSession)
    return provider


def get_broker() -> Provider:
    provider = Provider(scope=Scope.APP)
    provider.from_context(provides=RabbitBroker)
    return provider


def auth_services_provider() -> Provider:
    provider = Provider(scope=Scope.REQUEST)

    # Регистрируем зависимости
    provider.provide(source=TransactionManagerAlchemy, provides=TransactionManager)
    provider.provide(source=PasswordHasher)
    provider.provide(source=JWTServices)
    provider.provide(source=UserSqlAlchemyRepository, provides=UserAbstractRepository)
    provider.provide(source=GenerationUUID, provides=AbstractGenerationID)

    # Регистрируем основной сервис
    provider.provide(source=JWTAuthServices)

    return provider


def setup_providers() -> Iterable[Provider]:
    return (
        settings_provider(),
        get_broker(),
        db_provider(),
        auth_services_provider(),
    )
