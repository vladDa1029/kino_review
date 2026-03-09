from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class DomainEvent:
    event_type: str
    payload: dict[str, Any]
    correlation_id: str
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class ProjectMemberInvited(DomainEvent):
    project_id: UUID
    user_id: UUID


@dataclass(frozen=True, slots=True)
class ProjectMemberRoleChanged(DomainEvent):
    project_id: UUID
    user_id: UUID


@dataclass(frozen=True, slots=True)
class ShiftCreated(DomainEvent):
    project_id: UUID
    shift_id: UUID


@dataclass(frozen=True, slots=True)
class ShiftApproved(DomainEvent):
    project_id: UUID
    shift_id: UUID


@dataclass(frozen=True, slots=True)
class ShiftParticipantInvited(DomainEvent):
    shift_id: UUID
    participant_id: UUID
    user_id: UUID


@dataclass(frozen=True, slots=True)
class ShiftParticipantReserved(DomainEvent):
    shift_id: UUID
    participant_id: UUID
    user_id: UUID


@dataclass(frozen=True, slots=True)
class ResourceRequestCreated(DomainEvent):
    shift_id: UUID
    request_id: UUID


@dataclass(frozen=True, slots=True)
class ResourceRequestReserved(DomainEvent):
    shift_id: UUID
    request_id: UUID


@dataclass(frozen=True, slots=True)
class DocumentUploaded(DomainEvent):
    shift_id: UUID
    document_id: UUID
