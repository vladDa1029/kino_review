from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.enums import (
    DocumentStatus,
    DocumentType,
    ProjectMemberStatus,
    ProjectRole,
    ProjectStatus,
    ResourceRequestStatus,
    ShiftParticipantStatus,
    ShiftReminderStatus,
    ShiftReportActualityStatus,
    ShiftReportGenerationStatus,
    ShiftStatus,
)
from app.domain.value_objects import TimeInterval


@dataclass
class Project:
    title: str
    description: str
    owner_id: UUID
    status: ProjectStatus
    oid: UUID
    created_at: datetime
    updated_at: datetime


@dataclass
class ProjectMember:
    project_id: UUID
    user_id: UUID
    role: ProjectRole
    status: ProjectMemberStatus
    invited_by: UUID
    oid: UUID
    created_at: datetime
    updated_at: datetime

    @property
    def is_active(self) -> bool:
        return self.status == ProjectMemberStatus.ACTIVE


@dataclass
class Shift:
    oid: UUID
    project_id: UUID
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    created_by: UUID
    status: ShiftStatus
    created_at: datetime
    updated_at: datetime
    approved_by: UUID | None = None
    approved_at: datetime | None = None

    @property
    def interval(self) -> TimeInterval:
        return TimeInterval(start=self.start_time, end=self.end_time)


@dataclass
class ShiftParticipant:
    oid: UUID
    shift_id: UUID
    user_id: UUID
    role: ProjectRole
    time_from: datetime
    time_to: datetime
    status: ShiftParticipantStatus
    added_by: UUID
    created_at: datetime
    updated_at: datetime
    user_reservation_id: UUID | None = None
    reserve_failure_reason: str | None = None

    @property
    def interval(self) -> TimeInterval:
        return TimeInterval(start=self.time_from, end=self.time_to)


@dataclass
class Document:
    oid: UUID
    shift_id: UUID
    doc_type: DocumentType
    filename: str
    title: str
    storage_key: str
    bucket: str
    mime_type: str
    size: int
    owner_id: UUID
    version: int
    status: DocumentStatus
    created_at: datetime
    description: str | None = None


@dataclass
class ShiftResourceRequest:
    oid: UUID
    project_id: UUID
    shift_id: UUID
    resource_type: str
    resource_id: UUID
    resource_owner_user_id: UUID
    requested_by_user_id: UUID
    time_from: datetime
    time_to: datetime
    status: ResourceRequestStatus
    created_at: datetime
    updated_at: datetime
    resource_reservation_id: UUID | None = None
    rejection_reason: str | None = None
    reserve_failure_reason: str | None = None

    @property
    def interval(self) -> TimeInterval:
        return TimeInterval(start=self.time_from, end=self.time_to)


@dataclass
class ShiftReport:
    oid: UUID
    project_id: UUID
    shift_id: UUID
    version: int
    generation_status: ShiftReportGenerationStatus
    actuality_status: ShiftReportActualityStatus
    requested_by_user_id: UUID
    file_name: str | None
    bucket: str | None
    storage_key: str | None
    mime_type: str | None
    generated_at: datetime | None
    archived_at: datetime | None
    error_message: str | None
    stale_reason: str | None
    stale_marked_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass
class ReservationOutboxMessage:
    oid: UUID
    operation: str
    aggregate_id: UUID
    status: str
    attempts: int
    created_at: datetime
    updated_at: datetime
    last_error: str | None = None


@dataclass
class ShiftReminder:
    """Сущность уведомления о смене."""

    oid: UUID
    shift_id: UUID
    fire_at: datetime
    status: ShiftReminderStatus
    created_at: datetime
    updated_at: datetime
