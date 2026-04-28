from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.application.ports.broker import EventPublisher
from app.application.ports.domain import (
    ClockPort,
    DocumentRepository,
    ProjectMemberRepository,
    ResourceRequestRepository,
    ShiftParticipantRepository,
    ShiftRepository,
)
from app.domain.entities import (
    Document,
    ProjectMember,
    Shift,
    ShiftParticipant,
    ShiftResourceRequest,
)
from app.domain.errors.business import AccessDeniedError, EntityNotFoundError


@dataclass(frozen=True, slots=True)
class SystemClock(ClockPort):
    def now(self) -> datetime:
        return datetime.now(tz=UTC)


async def publish_best_effort(
    *,
    publisher: EventPublisher,
    topic: str,
    payload: dict[str, Any],
) -> None:
    try:
        await publisher.publish(topic, payload)
    except Exception:
        return None


async def get_actor_member(
    *,
    project_members: ProjectMemberRepository,
    project_id: UUID,
    user_id: UUID,
) -> ProjectMember:
    member = await project_members.get_by_project_and_user(
        project_id=project_id,
        user_id=user_id,
    )
    if member is None:
        raise AccessDeniedError("User is not a member of this project.")
    return member


async def require_active_project_member(
    *,
    project_members: ProjectMemberRepository,
    project_id: UUID,
    user_id: UUID,
    message: str = "User is not an active project member.",
) -> ProjectMember:
    member = await project_members.get_by_project_and_user(
        project_id=project_id,
        user_id=user_id,
    )
    if member is None or not member.is_active:
        raise EntityNotFoundError(message)
    return member


async def require_shift(*, shifts: ShiftRepository, shift_id: UUID) -> Shift:
    shift = await shifts.get_by_id(shift_id)
    if shift is None:
        raise EntityNotFoundError("Shift is not found.")
    return shift


async def require_participant(
    *,
    shift_participants: ShiftParticipantRepository,
    participant_id: UUID,
) -> ShiftParticipant:
    participant = await shift_participants.get_by_id(participant_id)
    if participant is None:
        raise EntityNotFoundError("Shift participant is not found.")
    return participant


async def require_resource_request(
    *,
    resource_requests: ResourceRequestRepository,
    request_id: UUID,
) -> ShiftResourceRequest:
    request = await resource_requests.get_by_id(request_id)
    if request is None:
        raise EntityNotFoundError("Resource request is not found.")
    return request


async def require_document(
    *,
    documents: DocumentRepository,
    document_id: UUID,
) -> Document:
    document = await documents.get_by_id(document_id)
    if document is None:
        raise EntityNotFoundError("Document is not found.")
    return document
