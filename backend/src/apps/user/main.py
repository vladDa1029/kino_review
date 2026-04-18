from contextlib import asynccontextmanager
from typing import cast

import structlog
from dishka import AsyncContainer, make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from faststream.rabbit import RabbitBroker

from app.config import (
    ConfirmationSettings,
    DatabaseSettings,
    ImageSettings,
    Log,
    ProjectService,
    Rabbitmq,
    SQLAlchemySettings,
    StorageSettings,
    get_settings,
)
from app.domain.errors.base import ApplicationError
from app.ioc import setup_providers
from app.infrastructure.adapters.broker import (
    PROJECT_EVENTS_EXCHANGE,
    SHIFT_PARTICIPANT_APPROVAL_REQUESTED_QUEUE,
    SHIFT_PARTICIPANT_RESERVATION_CHECK_REQUESTED_QUEUE,
    SHIFT_PARTICIPANT_RESERVATION_REQUESTED_QUEUE,
    SHIFT_RESOURCE_REQUEST_APPROVAL_REQUESTED_QUEUE,
    SHIFT_RESOURCE_REQUEST_RESERVATION_CHECK_REQUESTED_QUEUE,
    SHIFT_RESOURCE_REQUEST_RESERVATION_REQUESTED_QUEUE,
    USER_EVENTS_EXCHANGE,
    USER_REGISTERED_EXCHANGE,
    USER_EXISTENCE_REQUESTED_QUEUE,
    USER_REGISTERED_QUEUE,
)
from app.infrastructure.adapters.request_reply import BrokerReplyInbox, build_reply_queue
from app.infrastructure.adapters.orm import start_mappers
from app.presentation import handlers
from app.presentation.api import router as web_router
from app.presentation.broker import create_broker_router
from app.set_log import configure_logging

log = structlog.get_logger(__file__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    broker: RabbitBroker = cast(RabbitBroker, app.state._broker)
    reply_inbox = cast(BrokerReplyInbox, app.state.reply_inbox)
    await broker.start()
    await broker.declare_exchange(PROJECT_EVENTS_EXCHANGE)
    await broker.declare_exchange(USER_REGISTERED_EXCHANGE)
    await broker.declare_exchange(USER_EVENTS_EXCHANGE)
    await broker.declare_queue(build_reply_queue(reply_inbox))
    await broker.declare_queue(USER_REGISTERED_QUEUE)
    await broker.declare_queue(USER_EXISTENCE_REQUESTED_QUEUE)
    await broker.declare_queue(SHIFT_PARTICIPANT_RESERVATION_CHECK_REQUESTED_QUEUE)
    await broker.declare_queue(SHIFT_RESOURCE_REQUEST_RESERVATION_CHECK_REQUESTED_QUEUE)
    await broker.declare_queue(SHIFT_PARTICIPANT_APPROVAL_REQUESTED_QUEUE)
    await broker.declare_queue(SHIFT_RESOURCE_REQUEST_APPROVAL_REQUESTED_QUEUE)
    await broker.declare_queue(SHIFT_PARTICIPANT_RESERVATION_REQUESTED_QUEUE)
    await broker.declare_queue(SHIFT_RESOURCE_REQUEST_RESERVATION_REQUESTED_QUEUE)
    try:
        yield
    finally:
        await broker.stop()
        await cast(AsyncContainer, app.state.dishka_container).close()


def start_app_dev() -> FastAPI:
    app = FastAPI(
        lifespan=lifespan,
        debug=True,
        title="User service",
    )
    settings = get_settings()
    configure_logging(settings.log)
    broker = RabbitBroker(url=settings.rabbitmq.url)
    reply_inbox = BrokerReplyInbox(service_name="user")
    app.state._broker = broker
    app.state.reply_inbox = reply_inbox
    container: AsyncContainer = make_async_container(
        *setup_providers(),
        context={
            Log: settings.log,
            DatabaseSettings: settings.db,
            SQLAlchemySettings: settings.alchemy,
            Rabbitmq: settings.rabbitmq,
            StorageSettings: settings.storage,
            ImageSettings: settings.image,
            ProjectService: settings.project_service,
            ConfirmationSettings: settings.confirmation,
            BrokerReplyInbox: reply_inbox,
            RabbitBroker: broker,
        },
    )
    broker.include_router(create_broker_router(container, reply_inbox))
    setup_dishka(container=container, app=app)

    app.add_exception_handler(ApplicationError, handlers.application_error_handler)
    start_mappers()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8001",
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "Accept", "Cache-Control"],
    )
    app.include_router(web_router)
    log.info("Start application user!!!")
    return app
