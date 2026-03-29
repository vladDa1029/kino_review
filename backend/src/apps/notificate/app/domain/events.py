from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ParticipantApprovalNotification:
    request_id: UUID
    project_id: UUID
    shift_id: UUID
    participant_id: UUID
    user_id: UUID
    time_from: datetime
    time_to: datetime


@dataclass(frozen=True, slots=True)
class ResourceApprovalNotification:
    request_id: UUID
    project_id: UUID
    shift_id: UUID
    resource_request_id: UUID
    owner_user_id: UUID
    resource_id: UUID
    resource_type: str
    time_from: datetime
    time_to: datetime
