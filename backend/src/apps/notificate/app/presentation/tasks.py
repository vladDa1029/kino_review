from dishka import FromDishka
from dishka.integrations.taskiq import inject

from app.application.commands.send_email import (
    SendNotificationEmailCommand,
    SendNotificationEmailHandler,
)


SEND_NOTIFICATION_EMAIL_TASK_NAME = "notificate.send_notification_email"


@inject(patch_module=True)
async def send_notification_email_task(
    *,
    notification_id: str,
    recipient_email: str,
    subject: str,
    template: str,
    payload: dict[str, str | None],
    handler: FromDishka[SendNotificationEmailHandler],
) -> None:
    _ = notification_id
    await handler(
        SendNotificationEmailCommand(
            recipient_email=recipient_email,
            subject=subject,
            template=template,
            payload=payload,
        )
    )
