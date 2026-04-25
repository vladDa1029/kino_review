from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ShiftReportParticipantContext:
    participant_id: UUID
    user_id: UUID
    project_role: str
    shift_role: str
    time_from: datetime
    time_to: datetime


@dataclass(frozen=True, slots=True)
class ShiftReportResourceContext:
    resource_request_id: UUID
    resource_id: UUID
    owner_user_id: UUID
    resource_type: str
    time_from: datetime
    time_to: datetime


@dataclass(frozen=True, slots=True)
class ShiftReportUserDetails:
    user_id: UUID
    username: str | None
    phone: str | None
    email: str | None


@dataclass(frozen=True, slots=True)
class ShiftReportResourceDetails:
    resource_id: UUID
    owner_user_id: UUID
    title: str | None
    resource_type: str | None
    description: str | None
    size: str | None


@dataclass(frozen=True, slots=True)
class ShiftReportSnapshot:
    users: tuple[ShiftReportUserDetails, ...]
    resources: tuple[ShiftReportResourceDetails, ...]


class ShiftReportSnapshotPort(Protocol):
    async def fetch_snapshot(
        self,
        *,
        report_id: UUID,
        project_id: UUID,
        shift_id: UUID,
        participants: tuple[ShiftReportParticipantContext, ...],
        resources: tuple[ShiftReportResourceContext, ...],
    ) -> ShiftReportSnapshot:
        raise NotImplementedError


class ShiftReportRendererPort(Protocol):
    async def render(
        self,
        *,
        report_id: UUID,
        report_version: int,
        project_title: str,
        shift_title: str,
        shift_start_time: datetime,
        shift_end_time: datetime,
        actuality_status: str,
        generated_at: datetime,
        participants: tuple[dict[str, object], ...],
        owner_sections: tuple[dict[str, object], ...],
        external_owner_sections: tuple[dict[str, object], ...],
    ) -> bytes:
        raise NotImplementedError
