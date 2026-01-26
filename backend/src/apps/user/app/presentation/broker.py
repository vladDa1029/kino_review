from dishka import AsyncContainer
from faststream.rabbit import RabbitRouter

from app.application.commands.user_registered import (
    UserRegisteredCommand,
    UserRegisteredHandler,
)
from app.infrastructure.adapters.broker import (
    USER_REGISTERED_EXCHANGE,
    USER_REGISTERED_QUEUE,
)
from app.presentation.schemas import BrokerUserRegistered


def create_broker_router(container: AsyncContainer) -> RabbitRouter:
    router = RabbitRouter()

    @router.subscriber(USER_REGISTERED_QUEUE, exchange=USER_REGISTERED_EXCHANGE)
    async def handle_user_registered(event: BrokerUserRegistered) -> None:
        command = UserRegisteredCommand(
            user_id=event.user_id,
            email=event.email,
            is_active=event.is_active,
            is_superuser=event.is_superuser,
            is_verified=event.is_verified,
            create_at=event.create_at,
        )
        async with container() as request_container:
            handler = await request_container.get(UserRegisteredHandler)
            await handler(command)

    return router
