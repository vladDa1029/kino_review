from dishka import AsyncContainer
from dishka.integrations.taskiq import setup_dishka
import structlog
from taskiq import AsyncBroker, TaskiqEvents, TaskiqState

from app.bootstrap import (
    create_container,
    create_message_broker,
    create_task_manager,
    declare_worker_message_topology,
)
from app.config import get_settings
from app.infrastructure.adapters.orm import start_mappers
from app.infrastructure.broker.request_reply import BrokerReplyInbox
from app.infrastructure.storage.minio import ensure_minio_bucket
from app.presentation.broker import create_reply_router
from app.set_log import configure_logging

TASKIQ_CONTAINER_STATE_KEY = "taskiq_app_container"
TASKIQ_MESSAGE_BROKER_STATE_KEY = "taskiq_message_broker"
log = structlog.get_logger(__file__)


async def startup(state: TaskiqState) -> None:
    message_broker = state.get(TASKIQ_MESSAGE_BROKER_STATE_KEY)
    reply_inbox = state.get("reply_inbox")
    minio_settings = state.get("minio_settings")
    if message_broker is None or reply_inbox is None:
        return
    if minio_settings is not None:
        await _prepare_storage(component="worker", settings=minio_settings)
    await message_broker.start()
    await declare_worker_message_topology(message_broker, reply_inbox)


async def shutdown(state: TaskiqState) -> None:
    message_broker = state.get(TASKIQ_MESSAGE_BROKER_STATE_KEY)
    container = state.get(TASKIQ_CONTAINER_STATE_KEY)
    if message_broker is not None:
        await message_broker.stop()
    if isinstance(container, AsyncContainer):
        await container.close()


def create_worker_taskiq_app() -> AsyncBroker:
    settings = get_settings()
    configure_logging(settings.log)
    start_mappers()

    task_manager = create_task_manager(settings)
    message_broker = create_message_broker(settings)
    reply_inbox = BrokerReplyInbox(service_name="project")
    message_broker.include_router(create_reply_router(reply_inbox))

    container = create_container(
        settings,
        message_broker=message_broker,
        task_manager=task_manager,
        reply_inbox=reply_inbox,
    )

    task_manager.state[TASKIQ_CONTAINER_STATE_KEY] = container
    task_manager.state[TASKIQ_MESSAGE_BROKER_STATE_KEY] = message_broker
    task_manager.state["reply_inbox"] = reply_inbox
    task_manager.state["minio_settings"] = settings.minio
    task_manager.on_event(TaskiqEvents.WORKER_STARTUP)(startup)
    task_manager.on_event(TaskiqEvents.WORKER_SHUTDOWN)(shutdown)

    setup_dishka(container, broker=task_manager)
    return task_manager


async def _prepare_storage(*, component: str, settings) -> None:
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
