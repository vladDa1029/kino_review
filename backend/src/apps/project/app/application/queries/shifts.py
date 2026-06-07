from dataclasses import dataclass
from uuid import UUID

from app.application.ports.domain import (
    DocumentRepository,
    ProjectMemberRepository,
    ShiftParticipantRepository,
    ShiftRepository,
)
from app.application.support import get_actor_member, require_shift
from app.domain.entities import Document, Shift, ShiftParticipant
from app.domain.enums import (
    DocumentStatus,
    DocumentType,
    ShiftParticipantStatus,
    ShiftStatus,
)
from app.domain.policy.member_access import ActiveMemberPolicy


@dataclass(frozen=True, slots=True, kw_only=True)
class ListProjectShiftsQuery:
    project_id: UUID
    actor_user_id: UUID
    status_filter: ShiftStatus | None = None
    include_cancelled: bool = False


class ListProjectShiftsHandler:
    def __init__(
        self,
        *,
        shifts: ShiftRepository,
        project_members: ProjectMemberRepository,
        active_member_policy: ActiveMemberPolicy,
    ) -> None:
        self._shifts = shifts
        self._project_members = project_members
        self._active_member_policy = active_member_policy

    async def __call__(self, query: ListProjectShiftsQuery) -> list[Shift]:
        actor = await get_actor_member(
            project_members=self._project_members,
            project_id=query.project_id,
            user_id=query.actor_user_id,
        )
        self._active_member_policy.check(actor, action="list project shifts")
        return await self._shifts.list_by_project(
            query.project_id,
            include_cancelled=query.include_cancelled,
            status_filter=query.status_filter,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class GetShiftQuery:
    shift_id: UUID
    actor_user_id: UUID


class GetShiftHandler:
    def __init__(
        self,
        *,
        shifts: ShiftRepository,
        project_members: ProjectMemberRepository,
        active_member_policy: ActiveMemberPolicy,
    ) -> None:
        self._shifts = shifts
        self._project_members = project_members
        self._active_member_policy = active_member_policy

    async def __call__(self, query: GetShiftQuery) -> Shift:
        shift = await require_shift(shifts=self._shifts, shift_id=query.shift_id)
        actor = await get_actor_member(
            project_members=self._project_members,
            project_id=shift.project_id,
            user_id=query.actor_user_id,
        )
        self._active_member_policy.check(actor, action="view shift")
        return shift


@dataclass(frozen=True, slots=True, kw_only=True)
class ListShiftParticipantsQuery:
    shift_id: UUID
    actor_user_id: UUID
    include_cancelled: bool = False


class ListShiftParticipantsHandler:
    def __init__(
        self,
        *,
        shifts: ShiftRepository,
        shift_participants: ShiftParticipantRepository,
        project_members: ProjectMemberRepository,
        active_member_policy: ActiveMemberPolicy,
    ) -> None:
        self._shifts = shifts
        self._shift_participants = shift_participants
        self._project_members = project_members
        self._active_member_policy = active_member_policy

    async def __call__(self, query: ListShiftParticipantsQuery) -> list[ShiftParticipant]:
        shift = await require_shift(shifts=self._shifts, shift_id=query.shift_id)
        actor = await get_actor_member(
            project_members=self._project_members,
            project_id=shift.project_id,
            user_id=query.actor_user_id,
        )
        self._active_member_policy.check(actor, action="list shift participants")
        participants = await self._shift_participants.list_by_shift(query.shift_id)
        if query.include_cancelled:
            return participants
        return [
            participant
            for participant in participants
            if participant.status != ShiftParticipantStatus.CANCELLED
        ]


@dataclass(frozen=True, slots=True, kw_only=True)
class ListShiftDocumentsQuery:
    shift_id: UUID
    actor_user_id: UUID
    doc_type_filter: DocumentType | None = None


class ListShiftDocumentsHandler:
    def __init__(
        self,
        *,
        shifts: ShiftRepository,
        documents: DocumentRepository,
        project_members: ProjectMemberRepository,
        active_member_policy: ActiveMemberPolicy,
    ) -> None:
        self._shifts = shifts
        self._documents = documents
        self._project_members = project_members
        self._active_member_policy = active_member_policy

    async def __call__(self, query: ListShiftDocumentsQuery) -> list[Document]:
        shift = await require_shift(shifts=self._shifts, shift_id=query.shift_id)
        actor = await get_actor_member(
            project_members=self._project_members,
            project_id=shift.project_id,
            user_id=query.actor_user_id,
        )
        self._active_member_policy.check(actor, action="list shift documents")
        documents = await self._documents.list_by_shift(query.shift_id)
        return [
            document
            for document in documents
            if document.status == DocumentStatus.ACTIVE
            and (query.doc_type_filter is None or document.doc_type == query.doc_type_filter)
        ]
