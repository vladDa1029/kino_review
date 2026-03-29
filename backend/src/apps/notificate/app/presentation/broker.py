from dishka import AsyncContainer
from faststream.rabbit import RabbitRouter

from app.application.commands.schedule_notifications import (
    ScheduleNotificationEmailCommand,
    ScheduleNotificationEmailHandler,
)
from app.infrastructure.broker.queues import (
    NOTIFICATION_EMAIL_REQUESTED_QUEUE,
    USER_EVENTS_EXCHANGE,
)
from app.presentation.schemas import BrokerNotificationEmailRequested


def create_broker_router(container: AsyncContainer) -> RabbitRouter:
    router = RabbitRouter()

    @router.subscriber(NOTIFICATION_EMAIL_REQUESTED_QUEUE, exchange=USER_EVENTS_EXCHANGE)
    async def handle_notification_email_requested(
        event: BrokerNotificationEmailRequested,
    ) -> None:
        async with container() as request_container:
            handler = await request_container.get(ScheduleNotificationEmailHandler)
            await handler(
                ScheduleNotificationEmailCommand(
                    notification_id=event.notification_id,
                    recipient_email=event.recipient_email,
                    subject=event.subject,
                    template=event.template,
                    payload=event.payload.model_dump(),
                )
            )

    return router
