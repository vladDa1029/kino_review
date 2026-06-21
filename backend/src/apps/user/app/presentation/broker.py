from dishka import AsyncContainer
from faststream.rabbit import RabbitRouter

from app.application.commands.approval_notifications import (
    HandleParticipantApprovalRequestedCommand,
    HandleParticipantApprovalRequestedHandler,
    HandleProjectMemberInvitationRequestedCommand,
    HandleProjectMemberInvitationRequestedHandler,
    HandleResourceApprovalRequestedCommand,
    HandleResourceApprovalRequestedHandler,
    HandleShiftReminderRequestedCommand,
    HandleShiftReminderRequestedHandler,
    ShiftReminderResourceItem,
)
from app.application.commands.check_availability import (
    CheckAvailabilityCommand,
    CheckAvailabilityHandler,
)
from app.application.commands.reserve_availability import (
    ReserveAvailabilityCommand,
    ReserveAvailabilityHandler,
)
from app.application.commands.reserve_participant_availability import (
    ReserveParticipantAvailabilityCommand,
    ReserveParticipantAvailabilityHandler,
)
from app.application.commands.user_registered import (
    UserRegisteredCommand,
    UserRegisteredHandler,
)
from app.application.ports.broker import EventPublisher
from app.application.ports.repositories import UserRepository
from app.application.queries.report_snapshot import (
    ProvideShiftReportSnapshotHandler,
    ProvideShiftReportSnapshotQuery,
    ShiftReportParticipantContext,
    ShiftReportResourceContext,
)
from app.application.queries.users import (
    GetUserByEmailHandler,
    GetUserByEmailQuery,
    GetUserExistsHandler,
    GetUserExistsQuery,
)
from app.domain.entity.base import BaseId
from app.infrastructure.adapters.broker import (
    PROJECT_EVENTS_EXCHANGE,
    PROJECT_MEMBER_INVITATION_REQUESTED_QUEUE,
    SHIFT_PARTICIPANT_APPROVAL_REQUESTED_QUEUE,
    SHIFT_PARTICIPANT_RESERVATION_CHECK_REQUESTED_QUEUE,
    SHIFT_PARTICIPANT_RESERVATION_REQUESTED_QUEUE,
    SHIFT_REMINDER_REQUESTED_QUEUE,
    SHIFT_REPORT_SNAPSHOT_REQUESTED_QUEUE,
    SHIFT_RESOURCE_REQUEST_APPROVAL_REQUESTED_QUEUE,
    SHIFT_RESOURCE_REQUEST_RESERVATION_CHECK_REQUESTED_QUEUE,
    SHIFT_RESOURCE_REQUEST_RESERVATION_REQUESTED_QUEUE,
    USER_EMAIL_LOOKUP_REQUESTED_QUEUE,
    USER_EVENTS_EXCHANGE,
    USER_EXISTENCE_REQUESTED_QUEUE,
    USER_REGISTERED_EXCHANGE,
    USER_REGISTERED_QUEUE,
)
from app.infrastructure.adapters.request_reply import BrokerReplyInbox, build_reply_queue
from app.presentation.schemas import (
    BrokerProjectMemberInvitationRequested,
    BrokerShiftParticipantApprovalRequested,
    BrokerShiftParticipantReservationCheckRequested,
    BrokerShiftParticipantReservationRequested,
    BrokerShiftReminderRequested,
    BrokerShiftReportSnapshotRequested,
    BrokerShiftResourceRequestApprovalRequested,
    BrokerShiftResourceRequestReservationCheckRequested,
    BrokerShiftResourceRequestReservationRequested,
    BrokerUserEmailLookupRequested,
    BrokerUserExistenceRequested,
    BrokerUserRegistered,
)


def create_broker_router(container: AsyncContainer, reply_inbox: BrokerReplyInbox) -> RabbitRouter:
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

    @router.subscriber(USER_EXISTENCE_REQUESTED_QUEUE, exchange=PROJECT_EVENTS_EXCHANGE)
    async def handle_user_existence_requested(event: BrokerUserExistenceRequested) -> None:
        async with container() as request_container:
            handler = await request_container.get(GetUserExistsHandler)
            publisher = await request_container.get(EventPublisher)
            try:
                exists = await handler(GetUserExistsQuery(user_id=BaseId(event.user_id)))
            except Exception as exc:
                await publisher.publish(
                    event.reply_topic,
                    {
                        "correlation_id": str(event.correlation_id),
                        "response_type": "user.existence_failed",
                        "user_id": str(event.user_id),
                        "reason": str(exc),
                    },
                )
            else:
                await publisher.publish(
                    event.reply_topic,
                    {
                        "correlation_id": str(event.correlation_id),
                        "response_type": "user.existence_provided",
                        "user_id": str(event.user_id),
                        "exists": exists,
                    },
                )

    @router.subscriber(USER_EMAIL_LOOKUP_REQUESTED_QUEUE, exchange=PROJECT_EVENTS_EXCHANGE)
    async def handle_user_email_lookup_requested(event: BrokerUserEmailLookupRequested) -> None:
        async with container() as request_container:
            handler = await request_container.get(GetUserByEmailHandler)
            publisher = await request_container.get(EventPublisher)
            try:
                result = await handler(GetUserByEmailQuery(email=event.email))
            except Exception as exc:
                await publisher.publish(
                    event.reply_topic,
                    {
                        "correlation_id": str(event.correlation_id),
                        "response_type": "user.email_lookup_failed",
                        "email": event.email,
                        "reason": str(exc),
                    },
                )
            else:
                await publisher.publish(
                    event.reply_topic,
                    {
                        "correlation_id": str(event.correlation_id),
                        "response_type": "user.email_lookup_provided",
                        "email": result.email if result is not None else event.email,
                        "user_id": str(result.user_id) if result is not None else None,
                        "exists": result is not None,
                    },
                )

    @router.subscriber(SHIFT_REPORT_SNAPSHOT_REQUESTED_QUEUE, exchange=PROJECT_EVENTS_EXCHANGE)
    async def handle_shift_report_snapshot_requested(
        event: BrokerShiftReportSnapshotRequested,
    ) -> None:
        async with container() as request_container:
            handler = await request_container.get(ProvideShiftReportSnapshotHandler)
            publisher = await request_container.get(EventPublisher)
            try:
                snapshot = await handler(
                    ProvideShiftReportSnapshotQuery(
                        report_id=event.report_id,
                        participants=tuple(
                            ShiftReportParticipantContext(
                                participant_id=item.participant_id,
                                user_id=item.user_id,
                                project_role=item.project_role,
                                shift_role=item.shift_role,
                                time_from=item.time_from,
                                time_to=item.time_to,
                            )
                            for item in event.participants
                        ),
                        resources=tuple(
                            ShiftReportResourceContext(
                                resource_request_id=item.resource_request_id,
                                resource_id=item.resource_id,
                                owner_user_id=item.owner_user_id,
                                resource_type=item.resource_type,
                                time_from=item.time_from,
                                time_to=item.time_to,
                            )
                            for item in event.resources
                        ),
                    )
                )
            except Exception as exc:
                await publisher.publish(
                    event.reply_topic,
                    {
                        "correlation_id": str(event.correlation_id),
                        "response_type": "shift.report_snapshot_failed",
                        "report_id": str(event.report_id),
                        "reason": str(exc),
                    },
                )
            else:
                await publisher.publish(
                    event.reply_topic,
                    {
                        "correlation_id": str(event.correlation_id),
                        "response_type": "shift.report_snapshot_provided",
                        "report_id": str(event.report_id),
                        "users": snapshot["users"],
                        "resources": snapshot["resources"],
                    },
                )

    @router.subscriber(build_reply_queue(reply_inbox), exchange=PROJECT_EVENTS_EXCHANGE)
    async def handle_project_reply(event: dict) -> None:
        correlation_id = event.get("correlation_id")
        if isinstance(correlation_id, str):
            reply_inbox.resolve(correlation_id, event)

    @router.subscriber(
        SHIFT_PARTICIPANT_RESERVATION_CHECK_REQUESTED_QUEUE,
        exchange=PROJECT_EVENTS_EXCHANGE,
    )
    async def handle_participant_reservation_check_requested(
        event: BrokerShiftParticipantReservationCheckRequested,
    ) -> None:
        # For participants (people) we only verify they exist in this service's
        # database.  The free-time-window machinery (spare_time) is designed for
        # equipment/resources; applying it to people requires them to pre-register
        # their availability, which is not part of the current product flow.
        # The participant's own "Confirm" action on the website is their implicit
        # declaration of availability.
        async with container() as request_container:
            user_repo = await request_container.get(UserRepository)
            publisher = await request_container.get(EventPublisher)
            try:
                user = await user_repo.get(BaseId(event.user_id))
                if user is None:
                    raise ValueError(f"User {event.user_id} not found in user service.")
            except Exception as exc:
                await publisher.publish(
                    "shift.participant_reservation_check_failed",
                    {
                        "request_id": str(event.request_id),
                        "project_id": str(event.project_id),
                        "shift_id": str(event.shift_id),
                        "participant_id": str(event.participant_id),
                        "user_id": str(event.user_id),
                        "reason": str(exc),
                    },
                )
            else:
                await publisher.publish(
                    "shift.participant_reservation_check_succeeded",
                    {
                        "request_id": str(event.request_id),
                        "project_id": str(event.project_id),
                        "shift_id": str(event.shift_id),
                        "participant_id": str(event.participant_id),
                        "user_id": str(event.user_id),
                    },
                )

    @router.subscriber(
        SHIFT_RESOURCE_REQUEST_RESERVATION_CHECK_REQUESTED_QUEUE,
        exchange=PROJECT_EVENTS_EXCHANGE,
    )
    async def handle_resource_request_reservation_check_requested(
        event: BrokerShiftResourceRequestReservationCheckRequested,
    ) -> None:
        async with container() as request_container:
            handler = await request_container.get(CheckAvailabilityHandler)
            publisher = await request_container.get(EventPublisher)
            try:
                await handler(
                    CheckAvailabilityCommand(
                        user_id=BaseId(event.owner_user_id),
                        owner_id=BaseId(event.owner_user_id),
                        obj_id=BaseId(event.resource_id),
                        start_time=event.start_time,
                        end_time=event.end_time,
                    )
                )
            except Exception as exc:
                await publisher.publish(
                    "shift.resource_request_reservation_check_failed",
                    {
                        "request_id": str(event.request_id),
                        "project_id": str(event.project_id),
                        "shift_id": str(event.shift_id),
                        "resource_request_id": str(event.resource_request_id),
                        "owner_user_id": str(event.owner_user_id),
                        "resource_id": str(event.resource_id),
                        "reason": str(exc),
                    },
                )
            else:
                await publisher.publish(
                    "shift.resource_request_reservation_check_succeeded",
                    {
                        "request_id": str(event.request_id),
                        "project_id": str(event.project_id),
                        "shift_id": str(event.shift_id),
                        "resource_request_id": str(event.resource_request_id),
                        "owner_user_id": str(event.owner_user_id),
                        "resource_id": str(event.resource_id),
                    },
                )

    @router.subscriber(
        PROJECT_MEMBER_INVITATION_REQUESTED_QUEUE,
        exchange=PROJECT_EVENTS_EXCHANGE,
    )
    async def handle_project_member_invitation_requested(
        event: BrokerProjectMemberInvitationRequested,
    ) -> None:
        async with container() as request_container:
            handler = await request_container.get(HandleProjectMemberInvitationRequestedHandler)
            await handler(
                HandleProjectMemberInvitationRequestedCommand(
                    request_id=event.request_id,
                    project_id=event.project_id,
                    project_title=event.project_title,
                    member_id=event.member_id,
                    user_id=event.user_id,
                    role=event.role,
                    invited_by_user_id=event.invited_by_user_id,
                )
            )

    @router.subscriber(
        SHIFT_PARTICIPANT_APPROVAL_REQUESTED_QUEUE,
        exchange=PROJECT_EVENTS_EXCHANGE,
    )
    async def handle_participant_approval_requested(
        event: BrokerShiftParticipantApprovalRequested,
    ) -> None:
        async with container() as request_container:
            handler = await request_container.get(HandleParticipantApprovalRequestedHandler)
            await handler(
                HandleParticipantApprovalRequestedCommand(
                    request_id=event.request_id,
                    project_id=event.project_id,
                    project_title=event.project_title,
                    shift_id=event.shift_id,
                    shift_title=event.shift_title,
                    participant_id=event.participant_id,
                    user_id=event.user_id,
                    role=event.role,
                    time_from=event.time_from,
                    time_to=event.time_to,
                )
            )

    @router.subscriber(
        SHIFT_REMINDER_REQUESTED_QUEUE,
        exchange=PROJECT_EVENTS_EXCHANGE,
    )
    async def handle_shift_reminder_requested(
        event: BrokerShiftReminderRequested,
    ) -> None:
        async with container() as request_container:
            handler = await request_container.get(HandleShiftReminderRequestedHandler)
            await handler(
                HandleShiftReminderRequestedCommand(
                    notification_id=event.notification_id,
                    project_id=event.project_id,
                    project_title=event.project_title,
                    shift_id=event.shift_id,
                    shift_title=event.shift_title,
                    shift_description=event.shift_description,
                    start_time=event.start_time,
                    end_time=event.end_time,
                    user_id=event.user_id,
                    role=event.role,
                    resources=tuple(
                        ShiftReminderResourceItem(
                            resource_type=item.resource_type,
                            time_from=item.time_from,
                            time_to=item.time_to,
                        )
                        for item in event.resources
                    ),
                )
            )

    @router.subscriber(
        SHIFT_RESOURCE_REQUEST_APPROVAL_REQUESTED_QUEUE,
        exchange=PROJECT_EVENTS_EXCHANGE,
    )
    async def handle_resource_approval_requested(
        event: BrokerShiftResourceRequestApprovalRequested,
    ) -> None:
        async with container() as request_container:
            handler = await request_container.get(HandleResourceApprovalRequestedHandler)
            await handler(
                HandleResourceApprovalRequestedCommand(
                    request_id=event.request_id,
                    project_id=event.project_id,
                    project_title=event.project_title,
                    shift_id=event.shift_id,
                    shift_title=event.shift_title,
                    resource_request_id=event.resource_request_id,
                    owner_user_id=event.owner_user_id,
                    resource_id=event.resource_id,
                    resource_type=event.resource_type,
                    time_from=event.time_from,
                    time_to=event.time_to,
                )
            )

    @router.subscriber(
        SHIFT_PARTICIPANT_RESERVATION_REQUESTED_QUEUE,
        exchange=PROJECT_EVENTS_EXCHANGE,
    )
    async def handle_participant_reservation_requested(
        event: BrokerShiftParticipantReservationRequested,
    ) -> None:
        # Participants are people — no spare_time free windows needed.
        # ReserveParticipantAvailabilityHandler writes a "reserved" entry
        # directly into free_users_timing so the UI shows the occupied slot.
        async with container() as request_container:
            handler = await request_container.get(ReserveParticipantAvailabilityHandler)
            publisher = await request_container.get(EventPublisher)
            try:
                reservation_id = await handler(
                    ReserveParticipantAvailabilityCommand(
                        request_id=BaseId(event.request_id),
                        user_id=BaseId(event.user_id),
                        start_time=event.start_time,
                        end_time=event.end_time,
                    )
                )
            except Exception as exc:
                await publisher.publish(
                    "shift.participant_reserve_failed",
                    {
                        "request_id": str(event.request_id),
                        "project_id": str(event.project_id),
                        "shift_id": str(event.shift_id),
                        "participant_id": str(event.participant_id),
                        "user_id": str(event.user_id),
                        "reason": str(exc),
                    },
                )
            else:
                await publisher.publish(
                    "shift.participant_reserved.user",
                    {
                        "request_id": str(event.request_id),
                        "project_id": str(event.project_id),
                        "shift_id": str(event.shift_id),
                        "participant_id": str(event.participant_id),
                        "user_id": str(event.user_id),
                        "reservation_id": str(reservation_id),
                    },
                )

    @router.subscriber(
        SHIFT_RESOURCE_REQUEST_RESERVATION_REQUESTED_QUEUE,
        exchange=PROJECT_EVENTS_EXCHANGE,
    )
    async def handle_resource_request_reservation_requested(
        event: BrokerShiftResourceRequestReservationRequested,
    ) -> None:
        async with container() as request_container:
            handler = await request_container.get(ReserveAvailabilityHandler)
            publisher = await request_container.get(EventPublisher)
            try:
                reservation_id = await handler(
                    ReserveAvailabilityCommand(
                        request_id=BaseId(event.request_id),
                        user_id=BaseId(event.owner_user_id),
                        owner_id=BaseId(event.owner_user_id),
                        obj_id=BaseId(event.resource_id),
                        start_time=event.start_time,
                        end_time=event.end_time,
                    )
                )
            except Exception as exc:
                await publisher.publish(
                    "shift.resource_request_reserve_failed",
                    {
                        "request_id": str(event.request_id),
                        "project_id": str(event.project_id),
                        "shift_id": str(event.shift_id),
                        "resource_request_id": str(event.resource_request_id),
                        "owner_user_id": str(event.owner_user_id),
                        "resource_id": str(event.resource_id),
                        "reason": str(exc),
                    },
                )
            else:
                await publisher.publish(
                    "shift.resource_request_reserved.user",
                    {
                        "request_id": str(event.request_id),
                        "project_id": str(event.project_id),
                        "shift_id": str(event.shift_id),
                        "resource_request_id": str(event.resource_request_id),
                        "owner_user_id": str(event.owner_user_id),
                        "resource_id": str(event.resource_id),
                        "reservation_id": str(reservation_id),
                    },
                )

    return router
