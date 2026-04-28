from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ParticipantApprovalState:
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
    status: int
    status_name: str
    user_reservation_id: UUID | None
    reserve_failure_reason: str | None


@dataclass(frozen=True, slots=True)
class ResourceApprovalState:
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
    status: int
    status_name: str
    resource_reservation_id: UUID | None
    reserve_failure_reason: str | None


@dataclass(frozen=True, slots=True)
class ParticipantConfirmationTokenData:
    request_id: UUID
    project_id: UUID
    shift_id: UUID
    participant_id: UUID
    user_id: UUID
    time_from: datetime
    time_to: datetime


@dataclass(frozen=True, slots=True)
class ResourceConfirmationTokenData:
    request_id: UUID
    project_id: UUID
    shift_id: UUID
    resource_request_id: UUID
    owner_user_id: UUID
    resource_id: UUID
    time_from: datetime
    time_to: datetime


@dataclass(frozen=True, slots=True)
class ProjectMemberInvitationTokenData:
    request_id: UUID
    project_id: UUID
    member_id: UUID
    user_id: UUID
    role: str


class ProjectApprovalStatePort(Protocol):
    async def get_participant_approval_state(
        self,
        *,
        participant_id: UUID,
    ) -> ParticipantApprovalState:
        raise NotImplementedError

    async def get_resource_approval_state(
        self,
        *,
        resource_request_id: UUID,
    ) -> ResourceApprovalState:
        raise NotImplementedError


class ConfirmationTokenPort(Protocol):
    def issue_participant_token(
        self,
        *,
        request_id: UUID,
        project_id: UUID,
        shift_id: UUID,
        participant_id: UUID,
        user_id: UUID,
        time_from: datetime,
        time_to: datetime,
    ) -> str:
        raise NotImplementedError

    def issue_resource_token(
        self,
        *,
        request_id: UUID,
        project_id: UUID,
        shift_id: UUID,
        resource_request_id: UUID,
        owner_user_id: UUID,
        resource_id: UUID,
        time_from: datetime,
        time_to: datetime,
    ) -> str:
        raise NotImplementedError

    def issue_project_member_invitation_token(
        self,
        *,
        request_id: UUID,
        project_id: UUID,
        member_id: UUID,
        user_id: UUID,
        role: str,
    ) -> str:
        raise NotImplementedError

    def decode_confirmation_token(
        self,
        token: str,
    ) -> (
        ParticipantConfirmationTokenData
        | ResourceConfirmationTokenData
        | ProjectMemberInvitationTokenData
    ):
        raise NotImplementedError
