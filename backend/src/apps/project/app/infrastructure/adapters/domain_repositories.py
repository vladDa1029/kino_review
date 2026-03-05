from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.domain import (
    DocumentRepository,
    ProjectMemberRepository,
    ProjectRepository,
    ResourceRequestRepository,
    ShiftParticipantRepository,
    ShiftRepository,
)
from app.domain.entities import (
    Document,
    Project,
    ProjectMember,
    Shift,
    ShiftParticipant,
    ShiftResourceRequest,
)
from app.infrastructure.adapters.orm import shift_participants, users_project_role

T = TypeVar("T")


class SqlAlchemyRepository(Generic[T]):
    def __init__(self, session: AsyncSession, model: type[T]) -> None:
        self._session = session
        self._model = model

    async def add(self, entity: T) -> None:
        self._session.add(entity)

    async def get_by_id(self, reference: UUID) -> T | None:
        return await self._session.get(self._model, reference)

    async def update(self, entity: T) -> None:
        self._session.add(entity)


class SqlAlchemyProjectRepository(SqlAlchemyRepository[Project], ProjectRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Project)


class SqlAlchemyProjectMemberRepository(
    SqlAlchemyRepository[ProjectMember], ProjectMemberRepository
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ProjectMember)

    async def get_by_project_and_user(
        self, project_id: UUID, user_id: UUID
    ) -> ProjectMember | None:
        stmt = select(ProjectMember).where(
            users_project_role.c.project_id == project_id,
            users_project_role.c.user_id == user_id,
        )
        return (await self._session.execute(stmt)).scalars().first()


class SqlAlchemyShiftRepository(SqlAlchemyRepository[Shift], ShiftRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Shift)


class SqlAlchemyShiftParticipantRepository(
    SqlAlchemyRepository[ShiftParticipant], ShiftParticipantRepository
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ShiftParticipant)

    async def get_by_shift_and_user(self, shift_id: UUID, user_id: UUID) -> ShiftParticipant | None:
        stmt = select(ShiftParticipant).where(
            shift_participants.c.shift_id == shift_id,
            shift_participants.c.user_id == user_id,
        )
        return (await self._session.execute(stmt)).scalars().first()


class SqlAlchemyDocumentRepository(SqlAlchemyRepository[Document], DocumentRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Document)


class SqlAlchemyResourceRequestRepository(
    SqlAlchemyRepository[ShiftResourceRequest], ResourceRequestRepository
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ShiftResourceRequest)
