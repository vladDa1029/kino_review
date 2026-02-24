from typing import Iterable

from dishka import Provider, Scope
from sqlalchemy.ext.asyncio import AsyncSession
from faststream.rabbit import RabbitBroker

from app.application.ports.broker import EventPublisher
from app.application.ports.dispatcher import EventDispatcher
from app.application.ports.transaction import TransactionManager
from app.config import DatabaseSettings, Log, Rabbitmq, SQLAlchemySettings
from app.infrastructure.bazario.dispatcher import BazarioDispatcher
from app.infrastructure.broker.publisher import RabbitPublisher
from app.infrastructure.database import get_engine, get_session, get_sessionmaker
from app.infrastructure.transactions import TransactionManagerAlchemy
from app.application.queries.health import HealthHandler
from app.application.commands.publish_demo_event import PublishDemoEventHandler


def settings_provider() -> Provider:
    provider = Provider(scope=Scope.APP)
    provider.from_context(provides=Log)
    provider.from_context(provides=DatabaseSettings)
    provider.from_context(provides=SQLAlchemySettings)
    provider.from_context(provides=Rabbitmq)
    provider.from_context(provides=RabbitBroker)
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
    provider.provide(source=RabbitPublisher, provides=EventPublisher)
    return provider


def dispatcher_provider() -> Provider:
    provider = Provider(scope=Scope.APP)
    provider.provide(source=BazarioDispatcher, provides=EventDispatcher)
    return provider


def use_case_provider() -> Provider:
    provider = Provider(scope=Scope.REQUEST)
    provider.provide(source=HealthHandler)
    provider.provide(source=PublishDemoEventHandler)
    return provider


def setup_providers() -> Iterable[Provider]:
    return (
        settings_provider(),
        db_provider(),
        services_provider(),
        dispatcher_provider(),
        use_case_provider(),
    )
