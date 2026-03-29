from dataclasses import dataclass

from app.application.ports.tasks import NotificationTaskDispatcher


@dataclass(frozen=True, slots=True, kw_only=True)
class ScheduleNotificationEmailCommand:
    notification_id: str
    recipient_email: str
    subject: str
    template: str
    payload: dict[str, str | None]


class ScheduleNotificationEmailHandler:
    def __init__(self, *, dispatcher: NotificationTaskDispatcher) -> None:
        self._dispatcher = dispatcher

    async def __call__(self, command: ScheduleNotificationEmailCommand) -> None:
        await self._dispatcher.schedule_email(command)
