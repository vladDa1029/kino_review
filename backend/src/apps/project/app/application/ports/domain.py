from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.domain.entities import (
    Document,
    Project,
    ProjectMember,
    ReservationOutboxMessage,
    Shift,
    ShiftParticipant,
    ShiftReport,
    ShiftResourceRequest,
)


class ClockPort(Protocol):
    def now(self) -> datetime:
        raise NotImplementedError


class IdGeneratorPort(Protocol):
    def __call__(self) -> UUID:
        raise NotImplementedError


class ProjectRepository(Protocol):
    async def add(self, project: Project) -> None:
        raise NotImplementedError

    async def get_by_id(self, project_id: UUID) -> Project | None:
        raise NotImplementedError

    async def list_all(self, *, include_archived: bool = False) -> list[Project]:
        raise NotImplementedError

    async def list_by_user(self, user_id: UUID, *, include_archived: bool = False) -> list[Project]:
        raise NotImplementedError

    async def update(self, project: Project) -> None:
        raise NotImplementedError


class ProjectMemberRepository(Protocol):
    async def add(self, member: ProjectMember) -> None:
        raise NotImplementedError

    async def list_by_project(self, project_id: UUID) -> list[ProjectMember]:
        raise NotImplementedError

    async def get_by_project_and_user(
        self, project_id: UUID, user_id: UUID
    ) -> ProjectMember | None:
        raise NotImplementedError

    async def update(self, member: ProjectMember) -> None:
        raise NotImplementedError


class ShiftRepository(Protocol):
    async def add(self, shift: Shift) -> None:
        raise NotImplementedError

    async def get_by_id(self, shift_id: UUID) -> Shift | None:
        raise NotImplementedError

    async def update(self, shift: Shift) -> None:
        raise NotImplementedError


class ShiftParticipantRepository(Protocol):
    async def add(self, participant: ShiftParticipant) -> None:
        raise NotImplementedError

    async def get_by_id(self, participant_id: UUID) -> ShiftParticipant | None:
        raise NotImplementedError

    async def list_by_shift(self, shift_id: UUID) -> list[ShiftParticipant]:
        raise NotImplementedError

    async def get_by_shift_and_user(self, shift_id: UUID, user_id: UUID) -> ShiftParticipant | None:
        raise NotImplementedError

    async def update(self, participant: ShiftParticipant) -> None:
        raise NotImplementedError


class DocumentRepository(Protocol):
    async def add(self, document: Document) -> None:
        raise NotImplementedError

    async def get_by_id(self, document_id: UUID) -> Document | None:
        raise NotImplementedError

    async def list_by_shift(self, shift_id: UUID) -> list[Document]:
        raise NotImplementedError

    async def update(self, document: Document) -> None:
        raise NotImplementedError


class ResourceRequestRepository(Protocol):
    async def add(self, request: ShiftResourceRequest) -> None:
        raise NotImplementedError

    async def get_by_id(self, request_id: UUID) -> ShiftResourceRequest | None:
        raise NotImplementedError

    async def list_by_shift(self, shift_id: UUID) -> list[ShiftResourceRequest]:
        raise NotImplementedError

    async def update(self, request: ShiftResourceRequest) -> None:
        raise NotImplementedError


class ShiftReportRepository(Protocol):
    async def add(self, report: ShiftReport) -> None:
        raise NotImplementedError

    async def get_by_id(self, report_id: UUID) -> ShiftReport | None:
        raise NotImplementedError

    async def list_by_shift(self, shift_id: UUID) -> list[ShiftReport]:
        raise NotImplementedError

    async def update(self, report: ShiftReport) -> None:
        raise NotImplementedError


class ReservationOutboxRepository(Protocol):
    async def add(self, message: ReservationOutboxMessage) -> None:
        raise NotImplementedError

    async def get_by_id(self, message_id: UUID) -> ReservationOutboxMessage | None:
        raise NotImplementedError

    async def list_pending(self, *, limit: int) -> list[ReservationOutboxMessage]:
        raise NotImplementedError

    async def update(self, message: ReservationOutboxMessage) -> None:
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class UserResourceTimeWindow:
    window_id: UUID
    start_time: datetime
    end_time: datetime
    status: str


@dataclass(frozen=True, slots=True)
class UserResourceItem:
    resource_kind: str
    resource_id: UUID
    title: str
    description: str
    resource_type: str | None
    size: str | None
    created_at: datetime | None
    windows: tuple[UserResourceTimeWindow, ...] = ()


@dataclass(frozen=True, slots=True)
class UserIdentity:
    user_id: UUID
    email: str


class UserServicePort(Protocol):
    async def ensure_user_exists(self, user_id: UUID) -> None:
        raise NotImplementedError

    async def get_user_by_email(self, email: str) -> UserIdentity:
        raise NotImplementedError

    async def ensure_user_resource_exists(
        self,
        *,
        user_id: UUID,
        resource_kind: str,
        resource_id: UUID,
    ) -> None:
        raise NotImplementedError

    async def list_user_resources(
        self,
        *,
        user_id: UUID,
        resource_kinds: tuple[str, ...],
    ) -> list[UserResourceItem]:
        raise NotImplementedError

    async def reserve_user_time(
        self,
        *,
        request_id: UUID,
        user_id: UUID,
        time_from: datetime,
        time_to: datetime,
        project_id: UUID,
        shift_id: UUID,
        entity_id: UUID,
    ) -> None:
        raise NotImplementedError

    async def reserve_resource_time(
        self,
        *,
        request_id: UUID,
        owner_user_id: UUID,
        resource_id: UUID,
        time_from: datetime,
        time_to: datetime,
        project_id: UUID,
        shift_id: UUID,
        entity_id: UUID,
    ) -> None:
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class StoredFile:
    bucket: str
    storage_key: str
    size: int
    mime_type: str


class DocumentStoragePort(Protocol):
    async def upload(
        self,
        *,
        filename: str,
        content: bytes,
        content_type: str,
        storage_key: str | None = None,
    ) -> StoredFile:
        raise NotImplementedError

    async def get_download_url(self, *, storage_key: str) -> str:
        raise NotImplementedError
