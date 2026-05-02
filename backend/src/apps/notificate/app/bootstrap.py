from dishka import AsyncContainer, make_async_container
from faststream.rabbit import RabbitBroker
from taskiq import AsyncBroker
from taskiq.middlewares import SmartRetryMiddleware

from app.config import SMTP, Log, Rabbitmq, Settings, TaskIQ
from app.infrastructure.taskiq.broker import create_taskiq_broker
from app.ioc import setup_providers
from app.presentation.tasks import (
    SEND_NOTIFICATION_EMAIL_TASK_NAME,
    send_notification_email_task,
)


def create_container(
    settings: Settings,
    *,
    task_manager: AsyncBroker,
) -> AsyncContainer:
    return make_async_container(
        *setup_providers(),
        context={
            Log: settings.log,
            Rabbitmq: settings.rabbitmq,
            SMTP: settings.smtp,
            TaskIQ: settings.taskiq,
            AsyncBroker: task_manager,
        },
    )


def create_message_broker(settings: Settings) -> RabbitBroker:
    return RabbitBroker(url=settings.rabbitmq.url)


def create_task_manager(settings: Settings) -> AsyncBroker:
    broker = create_taskiq_broker(settings.rabbitmq.url, taskiq=settings.taskiq)
    setup_task_manager_middlewares(broker, settings.taskiq)
    setup_task_manager_tasks(broker, settings.taskiq)
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


def setup_task_manager_tasks(
    broker: AsyncBroker,
    taskiq: TaskIQ,
) -> None:
    if broker.find_task(SEND_NOTIFICATION_EMAIL_TASK_NAME) is not None:
        return

    broker.register_task(
        func=send_notification_email_task,
        task_name=SEND_NOTIFICATION_EMAIL_TASK_NAME,
        retry_on_error=True,
        max_retries=taskiq.default_retry_count,
        delay=taskiq.default_delay_seconds,
    )
