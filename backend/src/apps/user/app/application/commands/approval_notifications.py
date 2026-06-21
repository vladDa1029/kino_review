from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

import structlog

from app.application.ports.approvals import ConfirmationTokenPort
from app.application.ports.broker import EventPublisher
from app.application.ports.repositories import UserRepository
from app.config import ConfirmationSettings
from app.domain.entity.base import BaseId

log = structlog.get_logger(__name__)

EMAIL_REQUESTED_TOPIC = "notification.email_requested"


@dataclass(frozen=True, slots=True, kw_only=True)
class HandleParticipantApprovalRequestedCommand:
    request_id: UUID
    project_id: UUID
    project_title: str
    shift_id: UUID
    shift_title: str
    participant_id: UUID
    user_id: UUID
    role: str
    time_from: datetime
    time_to: datetime


class HandleParticipantApprovalRequestedHandler:
    def __init__(
        self,
        *,
        users: UserRepository,
        publisher: EventPublisher,
        confirmation_tokens: ConfirmationTokenPort,
        confirmation: ConfirmationSettings,
    ) -> None:
        self._users = users
        self._publisher = publisher
        self._confirmation_tokens = confirmation_tokens
        self._confirmation = confirmation

    async def __call__(
        self,
        command: HandleParticipantApprovalRequestedCommand,
    ) -> None:
        user = await self._users.get(BaseId(command.user_id))
        if user is None:
            log.warning(
                "approval.user_not_found",
                user_id=str(command.user_id),
                participant_id=str(command.participant_id),
                request_id=str(command.request_id),
            )
            return
        token = self._confirmation_tokens.issue_participant_token(
            request_id=command.request_id,
            project_id=command.project_id,
            shift_id=command.shift_id,
            participant_id=command.participant_id,
            user_id=command.user_id,
            time_from=command.time_from,
            time_to=command.time_to,
        )
        await self._publisher.publish(
            EMAIL_REQUESTED_TOPIC,
            {
                "notification_id": str(command.request_id),
                "template": "reservation_confirmation",
                "recipient_email": str(user.email),
                "subject": _participant_subject(command.shift_title),
                "payload": {
                    "confirm_url": _confirm_url(self._confirmation, token),
                    "project_title": command.project_title,
                    "shift_title": command.shift_title,
                    "time_from": command.time_from.isoformat(),
                    "time_to": command.time_to.isoformat(),
                    "role": command.role,
                    "resource_type": None,
                },
            },
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class HandleResourceApprovalRequestedCommand:
    request_id: UUID
    project_id: UUID
    project_title: str
    shift_id: UUID
    shift_title: str
    resource_request_id: UUID
    owner_user_id: UUID
    resource_id: UUID
    resource_type: str
    time_from: datetime
    time_to: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class HandleProjectMemberInvitationRequestedCommand:
    request_id: UUID
    project_id: UUID
    project_title: str
    member_id: UUID
    user_id: UUID
    role: str
    invited_by_user_id: UUID


class HandleResourceApprovalRequestedHandler:
    def __init__(
        self,
        *,
        users: UserRepository,
        publisher: EventPublisher,
        confirmation_tokens: ConfirmationTokenPort,
        confirmation: ConfirmationSettings,
    ) -> None:
        self._users = users
        self._publisher = publisher
        self._confirmation_tokens = confirmation_tokens
        self._confirmation = confirmation

    async def __call__(
        self,
        command: HandleResourceApprovalRequestedCommand,
    ) -> None:
        user = await self._users.get(BaseId(command.owner_user_id))
        if user is None:
            log.warning(
                "approval.resource_user_not_found",
                owner_user_id=str(command.owner_user_id),
                resource_request_id=str(command.resource_request_id),
                request_id=str(command.request_id),
            )
            return
        token = self._confirmation_tokens.issue_resource_token(
            request_id=command.request_id,
            project_id=command.project_id,
            shift_id=command.shift_id,
            resource_request_id=command.resource_request_id,
            owner_user_id=command.owner_user_id,
            resource_id=command.resource_id,
            time_from=command.time_from,
            time_to=command.time_to,
        )
        await self._publisher.publish(
            EMAIL_REQUESTED_TOPIC,
            {
                "notification_id": str(command.request_id),
                "template": "reservation_confirmation",
                "recipient_email": str(user.email),
                "subject": _resource_subject(command.shift_title),
                "payload": {
                    "confirm_url": _confirm_url(self._confirmation, token),
                    "project_title": command.project_title,
                    "shift_title": command.shift_title,
                    "time_from": command.time_from.isoformat(),
                    "time_to": command.time_to.isoformat(),
                    "role": None,
                    "resource_type": command.resource_type,
                },
            },
        )


class HandleProjectMemberInvitationRequestedHandler:
    def __init__(
        self,
        *,
        users: UserRepository,
        publisher: EventPublisher,
        confirmation_tokens: ConfirmationTokenPort,
        confirmation: ConfirmationSettings,
    ) -> None:
        self._users = users
        self._publisher = publisher
        self._confirmation_tokens = confirmation_tokens
        self._confirmation = confirmation

    async def __call__(
        self,
        command: HandleProjectMemberInvitationRequestedCommand,
    ) -> None:
        user = await self._users.get(BaseId(command.user_id))
        if user is None:
            log.warning(
                "approval.invitation_user_not_found",
                user_id=str(command.user_id),
                member_id=str(command.member_id),
                request_id=str(command.request_id),
            )
            return
        token = self._confirmation_tokens.issue_project_member_invitation_token(
            request_id=command.request_id,
            project_id=command.project_id,
            member_id=command.member_id,
            user_id=command.user_id,
            role=command.role,
        )
        await self._publisher.publish(
            EMAIL_REQUESTED_TOPIC,
            {
                "notification_id": str(command.request_id),
                "template": "project_member_invitation",
                "recipient_email": str(user.email),
                "subject": _project_member_invitation_subject(command.project_title),
                "payload": {
                    "accept_url": _project_invitation_url(self._confirmation, token),
                    "project_title": command.project_title,
                    "role": command.role,
                    "invited_by_user_id": str(command.invited_by_user_id),
                },
            },
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ShiftReminderResourceItem:
    resource_type: str
    time_from: datetime
    time_to: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class HandleShiftReminderRequestedCommand:
    notification_id: UUID
    project_id: UUID
    project_title: str
    shift_id: UUID
    shift_title: str
    shift_description: str | None
    start_time: datetime
    end_time: datetime
    user_id: UUID
    role: str
    resources: tuple[ShiftReminderResourceItem, ...] = field(default_factory=tuple)


class HandleShiftReminderRequestedHandler:
    def __init__(
        self,
        *,
        users: UserRepository,
        publisher: EventPublisher,
        confirmation: ConfirmationSettings,
    ) -> None:
        self._users = users
        self._publisher = publisher
        self._confirmation = confirmation

    async def __call__(self, command: HandleShiftReminderRequestedCommand) -> None:
        user = await self._users.get(BaseId(command.user_id))
        if user is None:
            log.warning(
                "reminder.user_not_found",
                user_id=str(command.user_id),
                shift_id=str(command.shift_id),
                notification_id=str(command.notification_id),
            )
            return
        await self._publisher.publish(
            EMAIL_REQUESTED_TOPIC,
            {
                "notification_id": str(command.notification_id),
                "template": "shift_reminder",
                "recipient_email": str(user.email),
                "subject": _shift_reminder_subject(command.shift_title),
                "payload": {
                    "shift_url": _shift_url(
                        self._confirmation,
                        project_id=command.project_id,
                        shift_id=command.shift_id,
                    ),
                    "project_title": command.project_title,
                    "shift_title": command.shift_title,
                    "time_from": command.start_time.isoformat(),
                    "time_to": command.end_time.isoformat(),
                    "role": command.role,
                    "resources": _format_resources(command.resources),
                },
            },
        )


def _format_resources(resources: tuple[ShiftReminderResourceItem, ...]) -> str | None:
    if not resources:
        return None
    lines = [
        f"- {item.resource_type} ({_format_time(item.time_from)} - {_format_time(item.time_to)})"
        for item in resources
    ]
    return "\n".join(lines)


def _format_time(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M")


def _shift_url(settings: ConfirmationSettings, *, project_id: UUID, shift_id: UUID) -> str:
    return f"{settings.frontend_base_url.rstrip('/')}/projects/{project_id}/shifts/{shift_id}"


def _shift_reminder_subject(shift_title: str) -> str:
    return f"Напоминание: смена «{shift_title}» скоро начнётся"


def _confirm_url(settings: ConfirmationSettings, token: str) -> str:
    return f"{settings.frontend_base_url.rstrip('/')}/confirm/{token}"


def _project_invitation_url(settings: ConfirmationSettings, token: str) -> str:
    return f"{settings.frontend_base_url.rstrip('/')}/invitations/{token}"


def _participant_subject(shift_title: str) -> str:
    return f"Подтвердите участие в смене «{shift_title}»"


def _resource_subject(shift_title: str) -> str:
    return f"Подтвердите бронирование ресурса для смены «{shift_title}»"


def _project_member_invitation_subject(project_title: str) -> str:
    return f"Приглашение в проект: {project_title}"
