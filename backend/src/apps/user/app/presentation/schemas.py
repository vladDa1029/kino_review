from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.application.common.pagination import MAX_PAGE_SIZE


class DescriptionCreateRequest(BaseModel):
    username: str = Field(examples=["Ivan Petrov"])
    phone: Annotated[str, Field(min_length=10, examples=["+79991234567"])]


class DescriptionUpdateRequest(BaseModel):
    username: str = Field(examples=["Ivan Petrov"])
    phone: str = Field(examples=["+79991234567"])


class DescriptionResponse(BaseModel):
    oid: UUID
    user_id: UUID
    username: str
    phone: str


class SpareTimeCreateRequest(BaseModel):
    start_time: datetime = Field(examples=["2026-01-15T10:00:00Z"])
    end_time: datetime = Field(examples=["2026-01-15T18:00:00Z"])


class SpareTimeResponse(BaseModel):
    oid: UUID
    user_id: UUID
    start_time: datetime
    end_time: datetime
    status: str


class SpareTimeListResponse(BaseModel):
    items: list[SpareTimeResponse]


class ReserveAvailabilityRequest(BaseModel):
    request_id: UUID = Field(examples=["8a0c6d4a-5d90-4b1b-8f4c-33df0f2a0ad7"])
    owner_id: UUID = Field(examples=["4a117f56-0f02-4d4d-9c25-51b2a778b6f6"])
    obj_id: UUID = Field(examples=["5f6a3b8f-3f68-4b15-9f1b-7f5c0b2f5c9a"])
    start_time: datetime = Field(examples=["2026-01-15T10:00:00Z"])
    end_time: datetime = Field(examples=["2026-01-15T12:00:00Z"])


class ReserveAvailabilityResponse(BaseModel):
    reservation_id: UUID = Field(examples=["5f6a3b8f-3f68-4b15-9f1b-7f5c0b2f5c9a"])


class EquipmentCreateRequest(BaseModel):
    title: str = Field(examples=["Sony A7S III"])
    description: str = Field(examples=["Full-frame mirrorless camera"])
    type: str = Field(examples=["mirrorless"])


class EquipmentUpdateRequest(BaseModel):
    title: str = Field(examples=["Sony A7S III"])
    description: str = Field(examples=["Updated description"])
    type: str = Field(examples=["mirrorless"])


class RequisiteCreateRequest(BaseModel):
    title: str = Field(examples=["Vintage lamp"])
    description: str = Field(examples=["Warm decorative lamp"])
    type: str = Field(examples=["decor"])
    size: str = Field(examples=["m"])


class RequisiteUpdateRequest(BaseModel):
    title: str = Field(examples=["Vintage lamp"])
    description: str = Field(examples=["Updated description"])
    type: str = Field(examples=["decor"])
    size: str = Field(examples=["m"])


class ImageCreateRequest(BaseModel):
    file: str = Field(examples=["lamp.jpg"])
    title: str = Field(examples=["Lamp photo"])
    storage_key: str = Field(examples=["requisites/abcd1234.jpg"])
    bucket: str = Field(examples=["user"])
    mime_type: str = Field(examples=["image/jpeg"])
    size: int = Field(examples=[245678])
    description: str = Field(examples=["Front view"])


class ImageResponse(BaseModel):
    oid: UUID
    requisite_id: UUID
    file: str
    title: str
    storage_key: str
    bucket: str
    mime_type: str
    size: int
    description: str
    create_at: datetime


class ImageListResponse(BaseModel):
    items: list[ImageResponse]


class BrokerUserRegistered(BaseModel):
    user_id: UUID = Field(examples=["0b8cf2c2-2a44-4fb8-aad8-9c37f2b6d8d4"])
    email: str = Field(examples=["user@example.com"])
    is_active: bool = Field(examples=[True])
    is_verified: bool = Field(examples=[True])
    is_superuser: bool = Field(examples=[False])
    create_at: datetime = Field(examples=["2026-01-10T09:30:00Z"])


class BrokerUserExistenceRequested(BaseModel):
    correlation_id: UUID
    reply_topic: str
    user_id: UUID


class BrokerUserEmailLookupRequested(BaseModel):
    correlation_id: UUID
    reply_topic: str
    email: str


class BrokerProjectMemberInvitationRequested(BaseModel):
    request_id: UUID
    project_id: UUID
    project_title: str
    member_id: UUID
    user_id: UUID
    role: str
    invited_by_user_id: UUID


class BrokerShiftParticipantReservationCheckRequested(BaseModel):
    request_id: UUID
    project_id: UUID
    shift_id: UUID
    participant_id: UUID
    user_id: UUID
    start_time: datetime
    end_time: datetime


class BrokerShiftResourceRequestReservationCheckRequested(BaseModel):
    request_id: UUID
    project_id: UUID
    shift_id: UUID
    resource_request_id: UUID
    owner_user_id: UUID
    resource_id: UUID
    start_time: datetime
    end_time: datetime


class BrokerShiftReminderResource(BaseModel):
    resource_type: str
    time_from: datetime
    time_to: datetime


class BrokerShiftReminderRequested(BaseModel):
    notification_id: UUID
    project_id: UUID
    project_title: str
    shift_id: UUID
    shift_title: str
    shift_description: str | None = None
    start_time: datetime
    end_time: datetime
    user_id: UUID
    role: str
    resources: list[BrokerShiftReminderResource] = Field(default_factory=list)


class BrokerShiftParticipantApprovalRequested(BaseModel):
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


class BrokerShiftResourceRequestApprovalRequested(BaseModel):
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


class BrokerShiftParticipantReservationRequested(BaseModel):
    request_id: UUID
    project_id: UUID
    shift_id: UUID
    participant_id: UUID
    user_id: UUID
    start_time: datetime
    end_time: datetime


class BrokerShiftResourceRequestReservationRequested(BaseModel):
    request_id: UUID
    project_id: UUID
    shift_id: UUID
    resource_request_id: UUID
    owner_user_id: UUID
    resource_id: UUID
    start_time: datetime
    end_time: datetime


class BrokerShiftParticipantApprovalStateReply(BaseModel):
    correlation_id: UUID
    response_type: Literal[
        "shift.participant_approval_state_provided",
        "shift.participant_approval_state_failed",
    ]
    participant_id: UUID | None = None
    request_id: UUID | None = None
    project_id: UUID | None = None
    project_title: str | None = None
    shift_id: UUID | None = None
    shift_title: str | None = None
    user_id: UUID | None = None
    role: str | None = None
    time_from: datetime | None = None
    time_to: datetime | None = None
    status: int | None = None
    status_name: str | None = None
    user_reservation_id: UUID | None = None
    reserve_failure_reason: str | None = None
    reason: str | None = None


class BrokerShiftResourceRequestApprovalStateReply(BaseModel):
    correlation_id: UUID
    response_type: Literal[
        "shift.resource_request_approval_state_provided",
        "shift.resource_request_approval_state_failed",
    ]
    resource_request_id: UUID | None = None
    request_id: UUID | None = None
    project_id: UUID | None = None
    project_title: str | None = None
    shift_id: UUID | None = None
    shift_title: str | None = None
    owner_user_id: UUID | None = None
    resource_id: UUID | None = None
    resource_type: str | None = None
    time_from: datetime | None = None
    time_to: datetime | None = None
    status: int | None = None
    status_name: str | None = None
    resource_reservation_id: UUID | None = None
    reserve_failure_reason: str | None = None
    reason: str | None = None


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


class EquipmentListQuery(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=MAX_PAGE_SIZE)
    sort_by: Literal["create_at", "title", "type"] | None = None
    sort_dir: Literal["asc", "desc"] = "asc"
    type: str | None = None
    search: str | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None


class RequisiteListQuery(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=MAX_PAGE_SIZE)
    sort_by: Literal["create_at", "title", "type", "size"] | None = None
    sort_dir: Literal["asc", "desc"] = "asc"
    type: str | None = None
    size: str | None = None
    search: str | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None


class EquipmentItemResponse(BaseModel):
    oid: UUID
    user_id: UUID
    title: str
    description: str
    type: str
    create_at: datetime


class RequisiteItemResponse(EquipmentItemResponse):
    size: str


class EquipmentListResponse(BaseModel):
    items: list[EquipmentItemResponse]
    page: int
    page_size: int
    total_count: int
    pages: int


class RequisiteListResponse(BaseModel):
    items: list[RequisiteItemResponse]
    page: int
    page_size: int
    total_count: int
    pages: int
