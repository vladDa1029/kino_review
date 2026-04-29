from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.entities import (
    Document,
    Project,
    ProjectMember,
    Shift,
    ShiftParticipant,
    ShiftReport,
    ShiftResourceRequest,
)
from app.domain.enums import (
    DocumentType,
    ProjectRole,
    ShiftReportActualityStatus,
    ShiftReportGenerationStatus,
)


class ProjectRoleInput(StrEnum):
    DIRECTOR = "DIRECTOR"
    PROP_MASTER = "PROP_MASTER"
    CAMERA = "CAMERA"
    SOUND = "SOUND"
    LIGHT = "LIGHT"
    ACTOR = "ACTOR"

    def to_domain(self) -> ProjectRole:
        return ProjectRole[self.value]


class DocumentTypeInput(StrEnum):
    PLAN = "PLAN"
    SCENARIO = "SCENARIO"

    def to_domain(self) -> DocumentType:
        return DocumentType[self.value]


def to_project_role_input(value: ProjectRole | int) -> ProjectRoleInput:
    role = value if isinstance(value, ProjectRole) else ProjectRole(int(value))
    return ProjectRoleInput[role.name]


class ProjectCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = ""


class ProjectUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)


class ProjectResponse(BaseModel):
    oid: UUID
    title: str
    description: str
    owner_id: UUID
    status: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, project: Project) -> ProjectResponse:
        return cls(
            oid=project.oid,
            title=project.title,
            description=project.description,
            owner_id=project.owner_id,
            status=int(project.status),
            created_at=project.created_at,
            updated_at=project.updated_at,
        )


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]


class InviteProjectMemberRequest(BaseModel):
    user_id: UUID
    role: ProjectRoleInput = Field(
        description="Role of invited user. Allowed values: DIRECTOR, PROP_MASTER, CAMERA, SOUND, LIGHT, ACTOR.",
    )


class InviteProjectMemberByEmailRequest(BaseModel):
    email: str = Field(
        min_length=3,
        max_length=255,
        pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
    )
    role: ProjectRoleInput = Field(
        description="Role of invited user. Allowed values: DIRECTOR, PROP_MASTER, CAMERA, SOUND, LIGHT, ACTOR.",
    )


class ProjectMemberResponse(BaseModel):
    oid: UUID
    project_id: UUID
    user_id: UUID
    role: ProjectRoleInput
    status: int
    invited_by: UUID
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, member: ProjectMember) -> ProjectMemberResponse:
        return cls(
            oid=member.oid,
            project_id=member.project_id,
            user_id=member.user_id,
            role=to_project_role_input(member.role),
            status=int(member.status),
            invited_by=member.invited_by,
            created_at=member.created_at,
            updated_at=member.updated_at,
        )


class ChangeProjectMemberRoleRequest(BaseModel):
    role: ProjectRoleInput = Field(
        description="New role in project. Allowed values: DIRECTOR, PROP_MASTER, CAMERA, SOUND, LIGHT, ACTOR.",
    )


class ProjectMemberShortResponse(BaseModel):
    oid: UUID
    user_id: UUID
    role: ProjectRoleInput
    status: int
    invited_by: UUID
    created_at: datetime
    updated_at: datetime


class ProjectMemberShortListResponse(BaseModel):
    items: list[ProjectMemberShortResponse]


class ProjectMemberListResponse(BaseModel):
    items: list[ProjectMemberShortResponse]


class ResourceTimeWindowResponse(BaseModel):
    window_id: UUID
    start_time: datetime
    end_time: datetime
    status: str


class ProjectResourceResponse(BaseModel):
    resource_kind: str
    resource_id: UUID
    title: str
    description: str
    resource_type: str | None
    size: str | None
    created_at: datetime | None
    windows: list[ResourceTimeWindowResponse]


class ProjectUserResourcesResponse(BaseModel):
    user_id: UUID
    role: ProjectRoleInput
    resources: list[ProjectResourceResponse]


class CreateShiftRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = ""
    start_time: datetime
    end_time: datetime


class ShiftResponse(BaseModel):
    oid: UUID
    project_id: UUID
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    status: int
    created_by: UUID
    approved_by: UUID | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, shift: Shift) -> ShiftResponse:
        return cls(
            oid=shift.oid,
            project_id=shift.project_id,
            title=shift.title,
            description=shift.description,
            start_time=shift.start_time,
            end_time=shift.end_time,
            status=int(shift.status),
            created_by=shift.created_by,
            approved_by=shift.approved_by,
            approved_at=shift.approved_at,
            created_at=shift.created_at,
            updated_at=shift.updated_at,
        )


class InviteShiftParticipantRequest(BaseModel):
    user_id: UUID
    role: ProjectRoleInput = Field(
        description="Participant role. Allowed values: DIRECTOR, PROP_MASTER, CAMERA, SOUND, LIGHT, ACTOR.",
    )
    time_from: datetime
    time_to: datetime


class ShiftParticipantResponse(BaseModel):
    oid: UUID
    shift_id: UUID
    user_id: UUID
    role: ProjectRoleInput
    time_from: datetime
    time_to: datetime
    status: int
    user_reservation_id: UUID | None
    reserve_failure_reason: str | None
    added_by: UUID
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, participant: ShiftParticipant) -> ShiftParticipantResponse:
        return cls(
            oid=participant.oid,
            shift_id=participant.shift_id,
            user_id=participant.user_id,
            role=to_project_role_input(participant.role),
            time_from=participant.time_from,
            time_to=participant.time_to,
            status=int(participant.status),
            user_reservation_id=participant.user_reservation_id,
            reserve_failure_reason=participant.reserve_failure_reason,
            added_by=participant.added_by,
            created_at=participant.created_at,
            updated_at=participant.updated_at,
        )


class ParticipantApprovalStateResponse(BaseModel):
    request_id: UUID
    project_id: UUID
    project_title: str
    shift_id: UUID
    shift_title: str
    participant_id: UUID
    user_id: UUID
    role: ProjectRoleInput
    time_from: datetime
    time_to: datetime
    status: int
    status_name: str
    user_reservation_id: UUID | None
    reserve_failure_reason: str | None


class CreateResourceRequestBody(BaseModel):
    resource_type: str = Field(min_length=1, max_length=64)
    resource_id: UUID
    resource_owner_user_id: UUID
    time_from: datetime
    time_to: datetime


class RejectResourceRequestBody(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


class ShiftResourceRequestResponse(BaseModel):
    oid: UUID
    project_id: UUID
    shift_id: UUID
    resource_type: str
    resource_id: UUID
    resource_owner_user_id: UUID
    requested_by_user_id: UUID
    time_from: datetime
    time_to: datetime
    status: int
    resource_reservation_id: UUID | None
    rejection_reason: str | None
    reserve_failure_reason: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, request: ShiftResourceRequest) -> ShiftResourceRequestResponse:
        return cls(
            oid=request.oid,
            project_id=request.project_id,
            shift_id=request.shift_id,
            resource_type=request.resource_type,
            resource_id=request.resource_id,
            resource_owner_user_id=request.resource_owner_user_id,
            requested_by_user_id=request.requested_by_user_id,
            time_from=request.time_from,
            time_to=request.time_to,
            status=int(request.status),
            resource_reservation_id=request.resource_reservation_id,
            rejection_reason=request.rejection_reason,
            reserve_failure_reason=request.reserve_failure_reason,
            created_at=request.created_at,
            updated_at=request.updated_at,
        )


class ResourceApprovalStateResponse(BaseModel):
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


class DocumentUploadResponse(BaseModel):
    oid: UUID
    shift_id: UUID
    doc_type: int
    filename: str
    title: str
    storage_key: str
    bucket: str
    mime_type: str
    size: int
    owner_id: UUID
    description: str | None
    version: int
    status: int
    created_at: datetime

    @classmethod
    def from_entity(cls, document: Document) -> DocumentUploadResponse:
        return cls(
            oid=document.oid,
            shift_id=document.shift_id,
            doc_type=int(document.doc_type),
            filename=document.filename,
            title=document.title,
            storage_key=document.storage_key,
            bucket=document.bucket,
            mime_type=document.mime_type,
            size=document.size,
            owner_id=document.owner_id,
            description=document.description,
            version=document.version,
            status=int(document.status),
            created_at=document.created_at,
        )


class DocumentDownloadUrlResponse(BaseModel):
    download_url: str


class ReportResponse(BaseModel):
    oid: UUID
    project_id: UUID
    shift_id: UUID
    version: int
    generation_status: int
    generation_status_name: str
    actuality_status: int
    actuality_status_name: str
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

    @classmethod
    def from_entity(cls, report: ShiftReport) -> "ReportResponse":
        generation_status = (
            report.generation_status
            if isinstance(report.generation_status, ShiftReportGenerationStatus)
            else ShiftReportGenerationStatus(int(report.generation_status))
        )
        actuality_status = (
            report.actuality_status
            if isinstance(report.actuality_status, ShiftReportActualityStatus)
            else ShiftReportActualityStatus(int(report.actuality_status))
        )
        return cls(
            oid=report.oid,
            project_id=report.project_id,
            shift_id=report.shift_id,
            version=report.version,
            generation_status=int(generation_status),
            generation_status_name=generation_status.name,
            actuality_status=int(actuality_status),
            actuality_status_name=actuality_status.name,
            requested_by_user_id=report.requested_by_user_id,
            file_name=report.file_name,
            bucket=report.bucket,
            storage_key=report.storage_key,
            mime_type=report.mime_type,
            generated_at=report.generated_at,
            archived_at=report.archived_at,
            error_message=report.error_message,
            stale_reason=report.stale_reason,
            stale_marked_at=report.stale_marked_at,
            created_at=report.created_at,
            updated_at=report.updated_at,
        )


class ReportListResponse(BaseModel):
    items: list[ReportResponse]


class BrokerProjectMemberInvitationApproved(BaseModel):
    project_id: UUID
    user_id: UUID
    approved_by_user_id: UUID | None = None


class BrokerUserExistenceReply(BaseModel):
    correlation_id: UUID
    response_type: Literal["user.existence_provided", "user.existence_failed"]
    user_id: UUID
    exists: bool | None = None
    reason: str | None = None


class BrokerUserEmailLookupReply(BaseModel):
    correlation_id: UUID
    response_type: Literal["user.email_lookup_provided", "user.email_lookup_failed"]
    email: str
    user_id: UUID | None = None
    exists: bool | None = None
    reason: str | None = None


class BrokerShiftParticipantReservationCheckSucceeded(BaseModel):
    request_id: UUID
    project_id: UUID
    shift_id: UUID
    participant_id: UUID
    user_id: UUID


class BrokerShiftParticipantReservationCheckFailed(BaseModel):
    request_id: UUID
    project_id: UUID
    shift_id: UUID
    participant_id: UUID
    user_id: UUID
    reason: str


class BrokerShiftParticipantReserved(BaseModel):
    request_id: UUID
    project_id: UUID
    shift_id: UUID
    participant_id: UUID
    user_id: UUID
    reservation_id: UUID


class BrokerShiftParticipantReserveFailed(BaseModel):
    request_id: UUID
    project_id: UUID
    shift_id: UUID
    participant_id: UUID
    user_id: UUID
    reason: str


class BrokerShiftResourceRequestReservationCheckSucceeded(BaseModel):
    request_id: UUID
    project_id: UUID
    shift_id: UUID
    resource_request_id: UUID
    owner_user_id: UUID
    resource_id: UUID


class BrokerShiftResourceRequestReservationCheckFailed(BaseModel):
    request_id: UUID
    project_id: UUID
    shift_id: UUID
    resource_request_id: UUID
    owner_user_id: UUID
    resource_id: UUID
    reason: str


class BrokerShiftResourceRequestReserved(BaseModel):
    request_id: UUID
    project_id: UUID
    shift_id: UUID
    resource_request_id: UUID
    owner_user_id: UUID
    resource_id: UUID
    reservation_id: UUID


class BrokerShiftResourceRequestReserveFailed(BaseModel):
    request_id: UUID
    project_id: UUID
    shift_id: UUID
    resource_request_id: UUID
    owner_user_id: UUID
    resource_id: UUID
    reason: str


class BrokerShiftParticipantApprovalStateRequested(BaseModel):
    correlation_id: UUID
    reply_topic: str
    participant_id: UUID


class BrokerShiftResourceRequestApprovalStateRequested(BaseModel):
    correlation_id: UUID
    reply_topic: str
    resource_request_id: UUID


class BrokerShiftReportParticipantContext(BaseModel):
    participant_id: UUID
    user_id: UUID
    project_role: str
    shift_role: str
    time_from: datetime
    time_to: datetime


class BrokerShiftReportResourceContext(BaseModel):
    resource_request_id: UUID
    resource_id: UUID
    owner_user_id: UUID
    resource_type: str
    time_from: datetime
    time_to: datetime


class BrokerShiftReportSnapshotRequested(BaseModel):
    correlation_id: UUID
    reply_topic: str
    report_id: UUID
    project_id: UUID
    shift_id: UUID
    participants: list[BrokerShiftReportParticipantContext]
    resources: list[BrokerShiftReportResourceContext]


class BrokerShiftReportUserDetails(BaseModel):
    user_id: UUID
    username: str | None = None
    phone: str | None = None
    email: str | None = None


class BrokerShiftReportResourceDetails(BaseModel):
    resource_id: UUID
    owner_user_id: UUID
    title: str | None = None
    resource_type: str | None = None
    description: str | None = None
    size: str | None = None


class BrokerShiftReportSnapshotReply(BaseModel):
    correlation_id: UUID
    response_type: Literal[
        "shift.report_snapshot_provided",
        "shift.report_snapshot_failed",
    ]
    report_id: UUID
    users: list[BrokerShiftReportUserDetails] = Field(default_factory=list)
    resources: list[BrokerShiftReportResourceDetails] = Field(default_factory=list)
    reason: str | None = None
