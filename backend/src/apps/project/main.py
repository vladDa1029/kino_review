import asyncio
from contextlib import asynccontextmanager
from time import perf_counter
from typing import cast
from uuid import uuid4

import structlog
from dishka import AsyncContainer
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from faststream.rabbit import RabbitBroker
from taskiq import AsyncBroker

from app.application.commands import (
    ProcessReservationOutboxHandler,
    ProcessShiftRemindersHandler,
)
from app.bootstrap import (
    create_container,
    create_message_broker,
    create_task_manager,
    declare_api_message_topology,
)
from app.config import (
    Minio,
    ReservationOutbox,
    get_settings,
)
from app.config import ShiftReminder as ShiftReminderSettings
from app.domain.errors.base import ApplicationError
from app.infrastructure.adapters.orm import start_mappers
from app.infrastructure.broker.request_reply import BrokerReplyInbox
from app.infrastructure.storage.minio import ensure_minio_bucket
from app.presentation import handlers
from app.presentation.api import (
    PROJECT_API_DESCRIPTION,
    PROJECT_OPENAPI_TAGS,
)
from app.presentation.api import (
    router as api_router,
)
from app.presentation.broker import create_broker_router
from app.set_log import configure_logging

log = structlog.get_logger(__file__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    broker: RabbitBroker = cast(RabbitBroker, app.state._broker)
    reply_inbox = cast(BrokerReplyInbox, app.state.reply_inbox)
    minio_settings = cast(Minio, app.state.minio_settings)
    task_manager = cast(AsyncBroker, app.state.task_manager)
    poll_task: asyncio.Task | None = None
    reminder_poll_task: asyncio.Task | None = None

    await _prepare_storage(component="api", settings=minio_settings)
    await task_manager.startup()

    broker_started = False
    try:
        await broker.start()
        await declare_api_message_topology(broker, reply_inbox)
        broker_started = True
    except Exception as exc:
        log.warning("RabbitMQ is unavailable, starting without broker", error=str(exc))

    async def poll_reservation_outbox() -> None:
        interval = cast(ReservationOutbox, app.state.reservation_outbox).poll_interval_seconds
        container = cast(AsyncContainer, app.state.dishka_container)
        while True:
            try:
                async with container() as request_container:
                    handler = await request_container.get(ProcessReservationOutboxHandler)
                    await handler(limit=20)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log.warning("reservation.outbox.poll_failed", error=str(exc))
            await asyncio.sleep(interval)

    async def poll_shift_reminders() -> None:
        interval = cast(ShiftReminderSettings, app.state.shift_reminder).poll_interval_seconds
        container = cast(AsyncContainer, app.state.dishka_container)
        while True:
            try:
                async with container() as request_container:
                    handler = await request_container.get(ProcessShiftRemindersHandler)
                    await handler(limit=50)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log.warning("shift.reminder.poll_failed", error=str(exc))
            await asyncio.sleep(interval)

    poll_task = asyncio.create_task(poll_reservation_outbox())
    reminder_poll_task = asyncio.create_task(poll_shift_reminders())

    try:
        yield
    finally:
        for background_task in (poll_task, reminder_poll_task):
            if background_task is not None:
                background_task.cancel()
                try:
                    await background_task
                except asyncio.CancelledError:
                    pass
        if broker_started:
            await broker.stop()
        await task_manager.shutdown()
        await cast(AsyncContainer, app.state.dishka_container).close()


async def _prepare_storage(*, component: str, settings: Minio) -> None:
    try:
        bucket_created = await ensure_minio_bucket(settings)
    except Exception:
        log.exception(
            "storage.startup.failed",
            component=component,
            bucket=settings.bucket,
            endpoint_url=settings.endpoint_url,
        )
        raise

    log.info(
        "storage.connection.ready",
        component=component,
        bucket=settings.bucket,
        endpoint_url=settings.endpoint_url,
    )
    log.info(
        "storage.bucket.created" if bucket_created else "storage.bucket.ready",
        component=component,
        bucket=settings.bucket,
        endpoint_url=settings.endpoint_url,
    )


def start_app_dev() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log)

    app = FastAPI(
        lifespan=lifespan,
        debug=True,
        title="Project service",
        version="0.1.0",
        description=PROJECT_API_DESCRIPTION,
        openapi_tags=PROJECT_OPENAPI_TAGS,
    )

    _SILENT_PATHS = {"/health"}

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        if request.url.path in _SILENT_PATHS:
            return await call_next(request)

        request_id = request.headers.get("X-Request-Id", str(uuid4()))
        started_at = perf_counter()
        request_logger = log.bind(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )
        request_logger.info("request.started")
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((perf_counter() - started_at) * 1000, 2)
            request_logger.exception(
                "request.failed",
                duration_ms=duration_ms,
            )
            raise

        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        response.headers["X-Request-Id"] = request_id
        status_code = response.status_code
        if status_code >= 500:
            request_logger.error(
                "request.completed",
                status_code=status_code,
                duration_ms=duration_ms,
            )
        elif status_code >= 400:
            request_logger.warning(
                "request.completed",
                status_code=status_code,
                duration_ms=duration_ms,
            )
        else:
            request_logger.info(
                "request.completed",
                status_code=status_code,
                duration_ms=duration_ms,
            )
        return response

    task_manager = create_task_manager(settings)
    reply_inbox = BrokerReplyInbox(service_name="project")
    broker = create_message_broker(settings)
    app.state._broker = broker
    app.state.reply_inbox = reply_inbox
    app.state.reservation_outbox = settings.reservation_outbox
    app.state.shift_reminder = settings.shift_rm
    app.state.minio_settings = settings.minio
    app.state.task_manager = task_manager

    container: AsyncContainer = create_container(
        settings,
        message_broker=broker,
        task_manager=task_manager,
        reply_inbox=reply_inbox,
    )
    broker.include_router(create_broker_router(container, reply_inbox))
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
        allow_headers=[
            "Content-Type",
            "Accept",
            "Cache-Control",
            "X-User-Id",
        ],
    )

    app.include_router(api_router)
    log.info("Start application project")
    return app
