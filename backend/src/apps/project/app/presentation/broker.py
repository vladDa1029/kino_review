from dishka import AsyncContainer
from faststream.rabbit import RabbitRouter

from app.application.commands import (
    ApproveProjectMemberInvitationCommand,
    ApproveProjectMemberInvitationHandler,
    HandleParticipantReservationCheckFailedCommand,
    HandleParticipantReservationCheckFailedHandler,
    HandleParticipantReservationCheckSucceededCommand,
    HandleParticipantReservationCheckSucceededHandler,
    HandleParticipantReservationFailedCommand,
    HandleParticipantReservationFailedHandler,
    HandleParticipantReservationSucceededCommand,
    HandleParticipantReservationSucceededHandler,
    HandleResourceReservationCheckFailedCommand,
    HandleResourceReservationCheckFailedHandler,
    HandleResourceReservationCheckSucceededCommand,
    HandleResourceReservationCheckSucceededHandler,
    HandleResourceReservationFailedCommand,
    HandleResourceReservationFailedHandler,
    HandleResourceReservationSucceededCommand,
    HandleResourceReservationSucceededHandler,
)
from app.infrastructure.broker.consumer import (
    PROJECT_MEMBER_APPROVED_QUEUE,
    SHIFT_PARTICIPANT_RESERVED_QUEUE,
    SHIFT_PARTICIPANT_RESERVATION_CHECK_FAILED_QUEUE,
    SHIFT_PARTICIPANT_RESERVATION_CHECK_SUCCEEDED_QUEUE,
    SHIFT_PARTICIPANT_RESERVE_FAILED_QUEUE,
    SHIFT_RESOURCE_REQUEST_RESERVED_QUEUE,
    SHIFT_RESOURCE_REQUEST_RESERVATION_CHECK_FAILED_QUEUE,
    SHIFT_RESOURCE_REQUEST_RESERVATION_CHECK_SUCCEEDED_QUEUE,
    SHIFT_RESOURCE_REQUEST_RESERVE_FAILED_QUEUE,
    USER_EVENTS_EXCHANGE,
)
from app.presentation.schemas import (
    BrokerProjectMemberInvitationApproved,
    BrokerShiftParticipantReservationCheckFailed,
    BrokerShiftParticipantReservationCheckSucceeded,
    BrokerShiftParticipantReserveFailed,
    BrokerShiftParticipantReserved,
    BrokerShiftResourceRequestReservationCheckFailed,
    BrokerShiftResourceRequestReservationCheckSucceeded,
    BrokerShiftResourceRequestReserveFailed,
    BrokerShiftResourceRequestReserved,
)


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

    @router.subscriber(
        SHIFT_PARTICIPANT_RESERVATION_CHECK_SUCCEEDED_QUEUE,
        exchange=USER_EVENTS_EXCHANGE,
    )
    async def handle_participant_reservation_check_succeeded(
        event: BrokerShiftParticipantReservationCheckSucceeded,
    ) -> None:
        command = HandleParticipantReservationCheckSucceededCommand(
            request_id=event.request_id,
            project_id=event.project_id,
            shift_id=event.shift_id,
            participant_id=event.participant_id,
            user_id=event.user_id,
        )
        async with container() as request_container:
            handler = await request_container.get(HandleParticipantReservationCheckSucceededHandler)
            await handler(command)

    @router.subscriber(
        SHIFT_PARTICIPANT_RESERVATION_CHECK_FAILED_QUEUE,
        exchange=USER_EVENTS_EXCHANGE,
    )
    async def handle_participant_reservation_check_failed(
        event: BrokerShiftParticipantReservationCheckFailed,
    ) -> None:
        command = HandleParticipantReservationCheckFailedCommand(
            participant_id=event.participant_id,
            reason=event.reason,
        )
        async with container() as request_container:
            handler = await request_container.get(HandleParticipantReservationCheckFailedHandler)
            await handler(command)

    @router.subscriber(SHIFT_PARTICIPANT_RESERVED_QUEUE, exchange=USER_EVENTS_EXCHANGE)
    async def handle_participant_reserved(event: BrokerShiftParticipantReserved) -> None:
        command = HandleParticipantReservationSucceededCommand(
            project_id=event.project_id,
            shift_id=event.shift_id,
            participant_id=event.participant_id,
            reservation_id=event.reservation_id,
        )
        async with container() as request_container:
            handler = await request_container.get(HandleParticipantReservationSucceededHandler)
            await handler(command)

    @router.subscriber(
        SHIFT_PARTICIPANT_RESERVE_FAILED_QUEUE,
        exchange=USER_EVENTS_EXCHANGE,
    )
    async def handle_participant_reserve_failed(
        event: BrokerShiftParticipantReserveFailed,
    ) -> None:
        command = HandleParticipantReservationFailedCommand(
            participant_id=event.participant_id,
            reason=event.reason,
        )
        async with container() as request_container:
            handler = await request_container.get(HandleParticipantReservationFailedHandler)
            await handler(command)

    @router.subscriber(
        SHIFT_RESOURCE_REQUEST_RESERVATION_CHECK_SUCCEEDED_QUEUE,
        exchange=USER_EVENTS_EXCHANGE,
    )
    async def handle_resource_request_reservation_check_succeeded(
        event: BrokerShiftResourceRequestReservationCheckSucceeded,
    ) -> None:
        command = HandleResourceReservationCheckSucceededCommand(
            request_id=event.request_id,
            project_id=event.project_id,
            shift_id=event.shift_id,
            resource_request_id=event.resource_request_id,
            owner_user_id=event.owner_user_id,
            resource_id=event.resource_id,
        )
        async with container() as request_container:
            handler = await request_container.get(HandleResourceReservationCheckSucceededHandler)
            await handler(command)

    @router.subscriber(
        SHIFT_RESOURCE_REQUEST_RESERVATION_CHECK_FAILED_QUEUE,
        exchange=USER_EVENTS_EXCHANGE,
    )
    async def handle_resource_request_reservation_check_failed(
        event: BrokerShiftResourceRequestReservationCheckFailed,
    ) -> None:
        command = HandleResourceReservationCheckFailedCommand(
            resource_request_id=event.resource_request_id,
            reason=event.reason,
        )
        async with container() as request_container:
            handler = await request_container.get(HandleResourceReservationCheckFailedHandler)
            await handler(command)

    @router.subscriber(SHIFT_RESOURCE_REQUEST_RESERVED_QUEUE, exchange=USER_EVENTS_EXCHANGE)
    async def handle_resource_request_reserved(
        event: BrokerShiftResourceRequestReserved,
    ) -> None:
        command = HandleResourceReservationSucceededCommand(
            project_id=event.project_id,
            shift_id=event.shift_id,
            resource_request_id=event.resource_request_id,
            reservation_id=event.reservation_id,
        )
        async with container() as request_container:
            handler = await request_container.get(HandleResourceReservationSucceededHandler)
            await handler(command)

    @router.subscriber(
        SHIFT_RESOURCE_REQUEST_RESERVE_FAILED_QUEUE,
        exchange=USER_EVENTS_EXCHANGE,
    )
    async def handle_resource_request_reserve_failed(
        event: BrokerShiftResourceRequestReserveFailed,
    ) -> None:
        command = HandleResourceReservationFailedCommand(
            resource_request_id=event.resource_request_id,
            reason=event.reason,
        )
        async with container() as request_container:
            handler = await request_container.get(HandleResourceReservationFailedHandler)
            await handler(command)

    return router
