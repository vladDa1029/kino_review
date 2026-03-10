from dishka import AsyncContainer
from faststream.rabbit import RabbitRouter

from app.application.commands import (
    ApproveProjectMemberInvitationCommand,
    ApproveProjectMemberInvitationHandler,
)
from app.infrastructure.broker.consumer import (
    PROJECT_MEMBER_APPROVED_QUEUE,
    USER_EVENTS_EXCHANGE,
)
from app.presentation.schemas import BrokerProjectMemberInvitationApproved


def create_broker_router(container: AsyncContainer) -> RabbitRouter:
    router = RabbitRouter()

    @router.subscriber(PROJECT_MEMBER_APPROVED_QUEUE, exchange=USER_EVENTS_EXCHANGE)
    async def handle_project_member_approved(
        event: BrokerProjectMemberInvitationApproved,
    ) -> None:
        command = ApproveProjectMemberInvitationCommand(
            project_id=event.project_id,
            user_id=event.user_id,
            approved_by_user_id=event.approved_by_user_id,
        )
        async with container() as request_container:
            handler = await request_container.get(ApproveProjectMemberInvitationHandler)
            await handler(command)

    return router
