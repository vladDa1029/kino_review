from typing import Iterable

import structlog
from dishka import Provider, Scope
from structlog.stdlib import BoundLogger
from taskiq import AsyncBroker

from app.application.commands.send_email import (
    SendNotificationEmailHandler,
)
from app.application.commands.schedule_notifications import (
    ScheduleNotificationEmailHandler,
)
from app.application.ports.email import EmailSender
from app.application.ports.tasks import NotificationTaskDispatcher
from app.application.queries.health import GetHealthHandler
from app.config import Log, Rabbitmq, SMTP, TaskIQ
from app.infrastructure.email.smtp import SMTPEmailSender
from app.infrastructure.taskiq.dispatcher import TaskiqNotificationTaskDispatcher


def settings_provider() -> Provider:
    provider = Provider(scope=Scope.APP)
    provider.from_context(provides=Log)
    provider.from_context(provides=Rabbitmq)
    provider.from_context(provides=SMTP)
    provider.from_context(provides=TaskIQ)
    provider.from_context(provides=AsyncBroker)
    return provider


def broker_provider() -> Provider:
    provider = Provider(scope=Scope.APP)
    provider.provide(
        source=TaskiqNotificationTaskDispatcher,
        provides=NotificationTaskDispatcher,
        scope=Scope.APP,
    )
    provider.provide(source=SMTPEmailSender, provides=EmailSender, scope=Scope.APP)
    return provider


def get_logger(settings: Log) -> BoundLogger:
    return structlog.get_logger(settings.logger_name)


def logger_provider() -> Provider:
    provider = Provider(scope=Scope.APP)
    provider.provide(get_logger, provides=BoundLogger)
    return provider


def use_case_provider() -> Provider:
    provider = Provider(scope=Scope.REQUEST)
    provider.provide(source=GetHealthHandler)
    provider.provide(source=ScheduleNotificationEmailHandler)
    provider.provide(source=SendNotificationEmailHandler)
    return provider


def setup_providers() -> Iterable[Provider]:
    return (
        settings_provider(),
        broker_provider(),
        logger_provider(),
        use_case_provider(),
    )
