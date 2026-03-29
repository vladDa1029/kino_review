from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.application.commands.schedule_notifications import (
        ScheduleNotificationEmailCommand,
    )


class NotificationTaskDispatcher(Protocol):
    async def schedule_email(
        self,
        command: "ScheduleNotificationEmailCommand",
    ) -> None:
        raise NotImplementedError
