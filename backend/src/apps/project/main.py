from contextlib import asynccontextmanager
from typing import cast

import structlog
from dishka import AsyncContainer, make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from faststream.rabbit import RabbitBroker

from app.config import (
    DatabaseSettings,
    Log,
    Minio,
    Rabbitmq,
    SQLAlchemySettings,
    UserService,
    get_settings,
)
from app.domain.errors.base import ApplicationError
from app.infrastructure.adapters.orm import start_mappers
from app.infrastructure.broker.publisher import PROJECT_EVENTS_EXCHANGE
from app.ioc import setup_providers
from app.presentation import handlers
from app.presentation.api import router as api_router
from app.set_log import configure_logging

log = structlog.get_logger(__file__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    broker: RabbitBroker = cast(RabbitBroker, app.state._broker)

    broker_started = False
    try:
        await broker.start()
        await broker.declare_exchange(PROJECT_EVENTS_EXCHANGE)
        broker_started = True
    except Exception as exc:
        log.warning("RabbitMQ is unavailable, starting without broker", error=str(exc))

    try:
        yield
    finally:
        if broker_started:
            await broker.stop()
        await cast(AsyncContainer, app.state.dishka_container).close()


def start_app_dev() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log)

    app = FastAPI(
        lifespan=lifespan,
        debug=True,
        title="Project service",
    )

    broker = RabbitBroker(url=settings.rabbitmq.url)
    app.state._broker = broker

    container: AsyncContainer = make_async_container(
        *setup_providers(),
        context={
            Log: settings.log,
            DatabaseSettings: settings.db,
            SQLAlchemySettings: settings.alchemy,
            Rabbitmq: settings.rabbitmq,
            UserService: settings.user_service,
            Minio: settings.minio,
            RabbitBroker: broker,
        },
    )
    setup_dishka(container=container, app=app)
    start_mappers()

    app.add_exception_handler(ApplicationError, handlers.application_error_handler)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "Accept", "Cache-Control", "X-User-Id"],
    )

    app.include_router(api_router)
    log.info("Start application project")
    return app
