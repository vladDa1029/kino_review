from taskiq import AsyncBroker

from app.application.commands.schedule_notifications import (
    ScheduleNotificationEmailCommand,
)
from app.application.ports.tasks import NotificationTaskDispatcher
from app.presentation.tasks import SEND_NOTIFICATION_EMAIL_TASK_NAME


class TaskiqNotificationTaskDispatcher(NotificationTaskDispatcher):
    def __init__(self, *, broker: AsyncBroker) -> None:
        self._broker = broker

    async def schedule_email(
        self,
        command: ScheduleNotificationEmailCommand,
    ) -> None:
        task = self._broker.find_task(SEND_NOTIFICATION_EMAIL_TASK_NAME)
        if task is None:
            msg = f"Task '{SEND_NOTIFICATION_EMAIL_TASK_NAME}' is not registered."
            raise RuntimeError(msg)

        await task.kiq(
            notification_id=command.notification_id,
            recipient_email=command.recipient_email,
            subject=command.subject,
            template=command.template,
            payload=command.payload,
        )
