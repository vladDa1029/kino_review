import asyncio
from contextlib import asynccontextmanager
from time import perf_counter
from typing import cast
from uuid import uuid4

import structlog
from dishka import AsyncContainer, make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from faststream.rabbit import RabbitBroker

from app.config import (
    DatabaseSettings,
    Log,
    Minio,
    Rabbitmq,
    ReservationOutbox,
    SQLAlchemySettings,
    UserService,
    get_settings,
)
from app.application.commands import ProcessReservationOutboxHandler
from app.domain.errors.base import ApplicationError
from app.infrastructure.adapters.orm import start_mappers
from app.infrastructure.broker.consumer import (
    PROJECT_MEMBER_APPROVED_QUEUE,
    SHIFT_PARTICIPANT_APPROVAL_STATE_REQUESTED_QUEUE,
    SHIFT_PARTICIPANT_RESERVED_QUEUE,
    SHIFT_PARTICIPANT_RESERVATION_CHECK_FAILED_QUEUE,
    SHIFT_PARTICIPANT_RESERVATION_CHECK_SUCCEEDED_QUEUE,
    SHIFT_PARTICIPANT_RESERVE_FAILED_QUEUE,
    SHIFT_RESOURCE_REQUEST_APPROVAL_STATE_REQUESTED_QUEUE,
    SHIFT_RESOURCE_REQUEST_RESERVED_QUEUE,
    SHIFT_RESOURCE_REQUEST_RESERVATION_CHECK_FAILED_QUEUE,
    SHIFT_RESOURCE_REQUEST_RESERVATION_CHECK_SUCCEEDED_QUEUE,
    SHIFT_RESOURCE_REQUEST_RESERVE_FAILED_QUEUE,
    USER_EVENTS_EXCHANGE,
)
from app.infrastructure.broker.publisher import PROJECT_EVENTS_EXCHANGE
from app.infrastructure.broker.request_reply import BrokerReplyInbox, build_reply_queue
from app.ioc import setup_providers
from app.presentation import handlers
from app.presentation.api import router as api_router
from app.presentation.broker import create_broker_router
from app.set_log import configure_logging

log = structlog.get_logger(__file__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    broker: RabbitBroker = cast(RabbitBroker, app.state._broker)
    reply_inbox = cast(BrokerReplyInbox, app.state.reply_inbox)
    poll_task: asyncio.Task | None = None

    broker_started = False
    try:
        await broker.start()
        await broker.declare_exchange(PROJECT_EVENTS_EXCHANGE)
        await broker.declare_exchange(USER_EVENTS_EXCHANGE)
        await broker.declare_queue(PROJECT_MEMBER_APPROVED_QUEUE)
        await broker.declare_queue(build_reply_queue(reply_inbox))
        await broker.declare_queue(SHIFT_PARTICIPANT_APPROVAL_STATE_REQUESTED_QUEUE)
        await broker.declare_queue(SHIFT_PARTICIPANT_RESERVATION_CHECK_SUCCEEDED_QUEUE)
        await broker.declare_queue(SHIFT_PARTICIPANT_RESERVATION_CHECK_FAILED_QUEUE)
        await broker.declare_queue(SHIFT_PARTICIPANT_RESERVED_QUEUE)
        await broker.declare_queue(SHIFT_PARTICIPANT_RESERVE_FAILED_QUEUE)
        await broker.declare_queue(SHIFT_RESOURCE_REQUEST_APPROVAL_STATE_REQUESTED_QUEUE)
        await broker.declare_queue(SHIFT_RESOURCE_REQUEST_RESERVATION_CHECK_SUCCEEDED_QUEUE)
        await broker.declare_queue(SHIFT_RESOURCE_REQUEST_RESERVATION_CHECK_FAILED_QUEUE)
        await broker.declare_queue(SHIFT_RESOURCE_REQUEST_RESERVED_QUEUE)
        await broker.declare_queue(SHIFT_RESOURCE_REQUEST_RESERVE_FAILED_QUEUE)
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

    poll_task = asyncio.create_task(poll_reservation_outbox())

    try:
        yield
    finally:
        if poll_task is not None:
            poll_task.cancel()
            try:
                await poll_task
            except asyncio.CancelledError:
                pass
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

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
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

    broker = RabbitBroker(url=settings.rabbitmq.url)
    reply_inbox = BrokerReplyInbox(service_name="project")
    app.state._broker = broker
    app.state.reply_inbox = reply_inbox
    app.state.reservation_outbox = settings.reservation_outbox

    container: AsyncContainer = make_async_container(
        *setup_providers(),
        context={
            Log: settings.log,
            DatabaseSettings: settings.db,
            SQLAlchemySettings: settings.alchemy,
            Rabbitmq: settings.rabbitmq,
            UserService: settings.user_service,
            BrokerReplyInbox: reply_inbox,
            ReservationOutbox: settings.reservation_outbox,
            Minio: settings.minio,
            RabbitBroker: broker,
        },
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
