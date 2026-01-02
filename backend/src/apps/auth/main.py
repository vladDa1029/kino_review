from contextlib import asynccontextmanager
from typing import cast
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dishka import AsyncContainer, make_async_container
from dishka.integrations.fastapi import setup_dishka
import structlog
from faststream.rabbit import RabbitBroker

from app.application.errors.errors import (
    InvalidCredentialsError,
    UserAlreadyError,
)
from app.config import (
    Auth,
    DatabaseSettings,
    Log,
    SQLAlchemySettings,
    get_settings,
)
from app.ioc import setup_providers
from app.infrastructure.adapters.broker import USER_REGISTERED_EXCHANGE
from app.infrastructure.adapters.orm import start_mappers
from app.infrastructure.errors.coder import NoValidTokenError
from app.presentations.api import router as auth_router
from app.presentations import handlers
from app.set_log import configure_logging

log = structlog.get_logger(__file__)

config = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    broker: RabbitBroker = cast("RabbitBroker", app.state._broker)

    await broker.start()
    await broker.declare_exchange(USER_REGISTERED_EXCHANGE)
    try:
        yield
    finally:
        await broker.stop()
        await cast(AsyncContainer, app.state.dishka_container).aclose()

    yield
    broker.stop()
    await cast("AsyncContainer", app.state.dishka_container).close()


def setup_start_test_app():

    app = FastAPI(lifespan=lifespan, debug=True, title="Сервис авторизации.")
    broker = RabbitBroker(url=config.rabbitmq.url)
    app.state._broker = broker
    context = {
        Log: config.log,
        Auth: config.auth,
        DatabaseSettings: config.db,
        SQLAlchemySettings: config.alchemy,
        RabbitBroker: broker,  # <-- ПЕРЕДАЁМ готовый экземпляр сюда
    }
    configure_logging(context[Log])

    # 3. Создаём DI-контейнер с контекстом, включая RabbitBroker
    container: AsyncContainer = make_async_container(
        *setup_providers(), context=context
    )

    # 4. Интегрируем контейнер с FastAPI
    setup_dishka(container=container, app=app)

    app.add_exception_handler(
        InvalidCredentialsError, handlers.invalid_credentials_exaption_handler
    )
    app.add_exception_handler(
        NoValidTokenError, handlers.no_valid_token_exaption_handler
    )
    app.add_exception_handler(
        UserAlreadyError, handlers.user_already_exists_exaption_handler
    )

    start_mappers()

    # Настройка для разработки с React/Vue
    origins = [
        "http://localhost:3000",  # React default
        "http://localhost:5173",  # Vite default
        "http://127.0.0.1:3000",  # Alternative
        "http://127.0.0.1:8001",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Accept",
            "Cache-Control",
        ],
        expose_headers=["Content-Disposition"],
    )
    app.include_router(auth_router)
    log.info("Start application auth!!!")
    return app
