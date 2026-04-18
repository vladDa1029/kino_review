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
from app.application.queries import (
    GetParticipantApprovalStateHandler,
    GetParticipantApprovalStateQuery,
    GetResourceApprovalStateHandler,
    GetResourceApprovalStateQuery,
)
from app.application.ports.broker import EventPublisher
from app.infrastructure.broker.consumer import (
    PROJECT_MEMBER_APPROVED_QUEUE,
    SHIFT_PARTICIPANT_APPROVAL_STATE_REQUESTED_QUEUE,
    SHIFT_PARTICIPANT_RESERVED_QUEUE,
    SHIFT_PARTICIPANT_RESERVATION_CHECK_FAILED_QUEUE,
    SHIFT_PARTICIPANT_RESERVATION_CHECK_SUCCEEDED_QUEUE,
    SHIFT_PARTICIPANT_RESERVE_FAILED_QUEUE,
    SHIFT_RESOURCE_REQUEST_APPROVAL_STATE_REQUESTED_QUEUE,
    SHIFT_RESOURCE_REQUEST_RESERVED_QUEUE,
    SHIFT_RESOURCE_REQUEST_RESERVATION_CHECK_FAILED_QUEUE,
    SHIFT_RESOURCE_REQUEST_RESERVATION_CHECK_SUCCEEDED_QUEUE,
    SHIFT_RESOURCE_REQUEST_RESERVE_FAILED_QUEUE,
    USER_EVENTS_EXCHANGE,
)
from app.infrastructure.broker.request_reply import BrokerReplyInbox, build_reply_queue
from app.presentation.schemas import (
    BrokerProjectMemberInvitationApproved,
    BrokerShiftParticipantApprovalStateRequested,
    BrokerShiftParticipantReservationCheckFailed,
    BrokerShiftParticipantReservationCheckSucceeded,
    BrokerShiftParticipantReserveFailed,
    BrokerShiftParticipantReserved,
    BrokerShiftResourceRequestApprovalStateRequested,
    BrokerShiftResourceRequestReservationCheckFailed,
    BrokerShiftResourceRequestReservationCheckSucceeded,
    BrokerShiftResourceRequestReserveFailed,
    BrokerShiftResourceRequestReserved,
    BrokerUserExistenceReply,
)


def create_broker_router(container: AsyncContainer, reply_inbox: BrokerReplyInbox) -> RabbitRouter:
    router = RabbitRouter()

    @router.subscriber(build_reply_queue(reply_inbox), exchange=USER_EVENTS_EXCHANGE)
    async def handle_user_reply(event: dict) -> None:
        try:
            reply = BrokerUserExistenceReply.model_validate(event)
        except Exception:
            return
        reply_inbox.resolve(str(reply.correlation_id), event)

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
        SHIFT_PARTICIPANT_APPROVAL_STATE_REQUESTED_QUEUE,
        exchange=USER_EVENTS_EXCHANGE,
    )
    async def handle_participant_approval_state_requested(
        event: BrokerShiftParticipantApprovalStateRequested,
    ) -> None:
        async with container() as request_container:
            handler = await request_container.get(GetParticipantApprovalStateHandler)
            publisher = await request_container.get(EventPublisher)
            try:
                result = await handler(
                    GetParticipantApprovalStateQuery(participant_id=event.participant_id)
                )
            except Exception as exc:
                await publisher.publish(
                    event.reply_topic,
                    {
                        "correlation_id": str(event.correlation_id),
                        "response_type": "shift.participant_approval_state_failed",
                        "participant_id": str(event.participant_id),
                        "reason": str(exc),
                    },
                )
            else:
                await publisher.publish(
                    event.reply_topic,
                    {
                        "correlation_id": str(event.correlation_id),
                        "response_type": "shift.participant_approval_state_provided",
                        "request_id": str(result.request_id),
                        "project_id": str(result.project_id),
                        "project_title": result.project_title,
                        "shift_id": str(result.shift_id),
                        "shift_title": result.shift_title,
                        "participant_id": str(result.participant_id),
                        "user_id": str(result.user_id),
                        "role": result.role_name,
                        "time_from": result.time_from.isoformat(),
                        "time_to": result.time_to.isoformat(),
                        "status": result.status,
                        "status_name": result.status_name,
                        "user_reservation_id": (
                            str(result.user_reservation_id)
                            if result.user_reservation_id is not None
                            else None
                        ),
                        "reserve_failure_reason": result.reserve_failure_reason,
                    },
                )

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

    @router.subscriber(
        SHIFT_RESOURCE_REQUEST_APPROVAL_STATE_REQUESTED_QUEUE,
        exchange=USER_EVENTS_EXCHANGE,
    )
    async def handle_resource_request_approval_state_requested(
        event: BrokerShiftResourceRequestApprovalStateRequested,
    ) -> None:
        async with container() as request_container:
            handler = await request_container.get(GetResourceApprovalStateHandler)
            publisher = await request_container.get(EventPublisher)
            try:
                result = await handler(
                    GetResourceApprovalStateQuery(resource_request_id=event.resource_request_id)
                )
            except Exception as exc:
                await publisher.publish(
                    event.reply_topic,
                    {
                        "correlation_id": str(event.correlation_id),
                        "response_type": "shift.resource_request_approval_state_failed",
                        "resource_request_id": str(event.resource_request_id),
                        "reason": str(exc),
                    },
                )
            else:
                await publisher.publish(
                    event.reply_topic,
                    {
                        "correlation_id": str(event.correlation_id),
                        "response_type": "shift.resource_request_approval_state_provided",
                        "request_id": str(result.request_id),
                        "project_id": str(result.project_id),
                        "project_title": result.project_title,
                        "shift_id": str(result.shift_id),
                        "shift_title": result.shift_title,
                        "resource_request_id": str(result.resource_request_id),
                        "owner_user_id": str(result.owner_user_id),
                        "resource_id": str(result.resource_id),
                        "resource_type": result.resource_type,
                        "time_from": result.time_from.isoformat(),
                        "time_to": result.time_to.isoformat(),
                        "status": result.status,
                        "status_name": result.status_name,
                        "resource_reservation_id": (
                            str(result.resource_reservation_id)
                            if result.resource_reservation_id is not None
                            else None
                        ),
                        "reserve_failure_reason": result.reserve_failure_reason,
                    },
                )

    return router
