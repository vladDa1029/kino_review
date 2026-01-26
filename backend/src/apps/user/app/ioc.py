from typing import Iterable

from dishka import Provider, Scope
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.transaction import TransactionManager
from app.config import DatabaseSettings, Log, Rabbitmq, SQLAlchemySettings
from app.infrastructure.database import get_engine, get_session, get_sessionmaker
from app.infrastructure.generation import AbstractGenerationID, GenerationUUID
from app.infrastructure.transactions import TransactionManagerAlchemy


def settings_provider() -> Provider:
    provider = Provider(scope=Scope.APP)
    provider.from_context(provides=Log)
    provider.from_context(provides=DatabaseSettings)
    provider.from_context(provides=SQLAlchemySettings)
    provider.from_context(provides=Rabbitmq)
    return provider


def db_provider() -> Provider:
    provider = Provider(scope=Scope.REQUEST)
    provider.provide(get_engine, scope=Scope.APP)
    provider.provide(get_sessionmaker, scope=Scope.APP)
    provider.provide(get_session, provides=AsyncSession)
    return provider


def services_provider() -> Provider:
    provider = Provider(scope=Scope.REQUEST)
    provider.provide(source=TransactionManagerAlchemy, provides=TransactionManager)
    provider.provide(source=GenerationUUID, provides=AbstractGenerationID)
    return provider


def setup_providers() -> Iterable[Provider]:
    return (
        settings_provider(),
        db_provider(),
        services_provider(),
    )
