from contextlib import asynccontextmanager
from typing import cast

import structlog
from dishka import AsyncContainer
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from faststream.rabbit import RabbitBroker
from taskiq import AsyncBroker

from app.bootstrap import create_container, create_message_broker, create_task_manager
from app.config import get_settings
from app.domain.errors.base import ApplicationError
from app.infrastructure.broker.queues import (
    NOTIFICATION_EMAIL_REQUESTED_QUEUE,
    USER_EVENTS_EXCHANGE,
)
from app.presentation import handlers
from app.presentation.api import router as api_router
from app.presentation.broker import create_broker_router
from app.set_log import configure_logging

log = structlog.get_logger(__file__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    broker: RabbitBroker = cast(RabbitBroker, app.state._broker)
    task_manager: AsyncBroker = cast(AsyncBroker, app.state.task_manager)
    await broker.start()
    await broker.declare_exchange(USER_EVENTS_EXCHANGE)
    await broker.declare_queue(NOTIFICATION_EMAIL_REQUESTED_QUEUE)
    if not task_manager.is_worker_process:
        await task_manager.startup()
    try:
        yield
    finally:
        if not task_manager.is_worker_process:
            await task_manager.shutdown()
        await broker.stop()
        await cast(AsyncContainer, app.state.dishka_container).close()


def start_app_dev() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log)

    app = FastAPI(
        lifespan=lifespan,
        debug=True,
        title="Notificate service",
    )

    broker = create_message_broker(settings)
    app.state._broker = broker
    task_manager = create_task_manager(settings)
    app.state.task_manager = task_manager

    container: AsyncContainer = create_container(settings, task_manager=task_manager)
    broker.include_router(create_broker_router(container))
    setup_dishka(container=container, app=app)
    app.add_exception_handler(ApplicationError, handlers.application_error_handler)
    app.include_router(api_router)
    log.info("Start application notificate")
    return app
