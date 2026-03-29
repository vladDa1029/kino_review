from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.application.ports.approvals import ConfirmationTokenPort
from app.application.ports.broker import EventPublisher
from app.application.ports.repositories import UserRepository
from app.config import ConfirmationSettings
from app.domain.entity.base import BaseId


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


def _confirm_url(settings: ConfirmationSettings, token: str) -> str:
    return f"{settings.public_base_url.rstrip('/')}/user/confirmations/{token}"


def _participant_subject(shift_title: str) -> str:
    return f"Confirm reservation for shift '{shift_title}'"


def _resource_subject(shift_title: str) -> str:
    return f"Confirm resource reservation for shift '{shift_title}'"
