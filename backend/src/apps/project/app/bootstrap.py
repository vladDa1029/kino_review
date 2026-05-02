from dishka import AsyncContainer, make_async_container
from faststream.rabbit import RabbitBroker
from taskiq import AsyncBroker
from taskiq.middlewares import SmartRetryMiddleware

from app.config import (
    DatabaseSettings,
    Log,
    Minio,
    Rabbitmq,
    ReportGeneration,
    ReservationOutbox,
    Settings,
    SQLAlchemySettings,
    TaskIQ,
    UserService,
)
from app.infrastructure.broker.consumer import (
    PROJECT_MEMBER_APPROVED_QUEUE,
    SHIFT_PARTICIPANT_APPROVAL_STATE_REQUESTED_QUEUE,
    SHIFT_PARTICIPANT_RESERVATION_CHECK_FAILED_QUEUE,
    SHIFT_PARTICIPANT_RESERVATION_CHECK_SUCCEEDED_QUEUE,
    SHIFT_PARTICIPANT_RESERVE_FAILED_QUEUE,
    SHIFT_PARTICIPANT_RESERVED_QUEUE,
    SHIFT_RESOURCE_REQUEST_APPROVAL_STATE_REQUESTED_QUEUE,
    SHIFT_RESOURCE_REQUEST_RESERVATION_CHECK_FAILED_QUEUE,
    SHIFT_RESOURCE_REQUEST_RESERVATION_CHECK_SUCCEEDED_QUEUE,
    SHIFT_RESOURCE_REQUEST_RESERVE_FAILED_QUEUE,
    SHIFT_RESOURCE_REQUEST_RESERVED_QUEUE,
    USER_EVENTS_EXCHANGE,
)
from app.infrastructure.broker.publisher import PROJECT_EVENTS_EXCHANGE
from app.infrastructure.broker.request_reply import BrokerReplyInbox, build_reply_queue
from app.infrastructure.taskiq.broker import create_taskiq_broker
from app.ioc import setup_providers
from app.presentation.tasks import (
    PROCESS_SHIFT_REPORT_TASK_NAME,
    process_shift_report_generation_task,
)


def create_container(
    settings: Settings,
    *,
    message_broker: RabbitBroker,
    task_manager: AsyncBroker,
    reply_inbox: BrokerReplyInbox,
) -> AsyncContainer:
    return make_async_container(
        *setup_providers(),
        context={
            Log: settings.log,
            DatabaseSettings: settings.db,
            SQLAlchemySettings: settings.alchemy,
            Rabbitmq: settings.rabbitmq,
            UserService: settings.user_service,
            BrokerReplyInbox: reply_inbox,
            ReservationOutbox: settings.reservation_outbox,
            TaskIQ: settings.taskiq,
            ReportGeneration: settings.report_generation,
            Minio: settings.minio,
            RabbitBroker: message_broker,
            AsyncBroker: task_manager,
        },
    )


def create_message_broker(settings: Settings) -> RabbitBroker:
    return RabbitBroker(url=settings.rabbitmq.url)


def create_task_manager(settings: Settings) -> AsyncBroker:
    broker = create_taskiq_broker(settings.rabbitmq.url, taskiq=settings.taskiq)
    setup_task_manager_middlewares(broker, settings.taskiq)
    setup_task_manager_tasks(broker)
    return broker


def setup_task_manager_middlewares(
    broker: AsyncBroker,
    taskiq: TaskIQ,
) -> None:
    broker.add_middlewares(
        SmartRetryMiddleware(
            default_retry_count=taskiq.default_retry_count,
            default_delay=taskiq.default_delay_seconds,
            use_jitter=taskiq.use_jitter,
            use_delay_exponent=taskiq.use_delay_exponent,
            max_delay_exponent=taskiq.max_delay_exponent,
        )
    )


def setup_task_manager_tasks(broker: AsyncBroker) -> None:
    if broker.find_task(PROCESS_SHIFT_REPORT_TASK_NAME) is not None:
        return
    broker.register_task(
        func=process_shift_report_generation_task,
        task_name=PROCESS_SHIFT_REPORT_TASK_NAME,
        retry_on_error=True,
    )


async def declare_api_message_topology(
    broker: RabbitBroker,
    reply_inbox: BrokerReplyInbox,
) -> None:
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


async def declare_worker_message_topology(
    broker: RabbitBroker,
    reply_inbox: BrokerReplyInbox,
) -> None:
    await broker.declare_exchange(PROJECT_EVENTS_EXCHANGE)
    await broker.declare_exchange(USER_EVENTS_EXCHANGE)
    await broker.declare_queue(build_reply_queue(reply_inbox))
