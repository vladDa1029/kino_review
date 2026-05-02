from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.domain import (
    DocumentRepository,
    ProjectMemberRepository,
    ProjectRepository,
    ReservationOutboxRepository,
    ResourceRequestRepository,
    ShiftParticipantRepository,
    ShiftReportRepository,
    ShiftRepository,
)
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
from app.domain.enums import ProjectMemberStatus, ProjectStatus
from app.infrastructure.adapters.orm import documents as documents_table
from app.infrastructure.adapters.orm import projects as projects_table
from app.infrastructure.adapters.orm import reservation_outbox, shift_participants, users_project_role
from app.infrastructure.adapters.orm import shift_reports as shift_reports_table

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

    async def list_all(self, *, include_archived: bool = False) -> list[Project]:
        stmt = select(Project)
        if not include_archived:
            stmt = stmt.where(projects_table.c.status != int(ProjectStatus.ARCHIVED))
        stmt = stmt.order_by(projects_table.c.created_at.desc())
        return list((await self._session.execute(stmt)).scalars().all())

    async def list_by_user(self, user_id: UUID, *, include_archived: bool = False) -> list[Project]:
        stmt = (
            select(Project)
            .join(
                users_project_role,
                users_project_role.c.project_id == projects_table.c.oid,
            )
            .where(
                users_project_role.c.user_id == user_id,
                users_project_role.c.status == int(ProjectMemberStatus.ACTIVE),
            )
        )
        if not include_archived:
            stmt = stmt.where(projects_table.c.status != int(ProjectStatus.ARCHIVED))
        return list((await self._session.execute(stmt)).scalars().all())


class SqlAlchemyProjectMemberRepository(
    SqlAlchemyRepository[ProjectMember], ProjectMemberRepository
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ProjectMember)

    async def list_by_project(self, project_id: UUID) -> list[ProjectMember]:
        stmt = select(ProjectMember).where(users_project_role.c.project_id == project_id)
        return list((await self._session.execute(stmt)).scalars().all())

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

    async def list_by_shift(self, shift_id: UUID) -> list[ShiftParticipant]:
        stmt = select(ShiftParticipant).where(shift_participants.c.shift_id == shift_id)
        return list((await self._session.execute(stmt)).scalars().all())

    async def get_by_shift_and_user(self, shift_id: UUID, user_id: UUID) -> ShiftParticipant | None:
        stmt = select(ShiftParticipant).where(
            shift_participants.c.shift_id == shift_id,
            shift_participants.c.user_id == user_id,
        )
        return (await self._session.execute(stmt)).scalars().first()


class SqlAlchemyDocumentRepository(SqlAlchemyRepository[Document], DocumentRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Document)

    async def list_by_shift(self, shift_id: UUID) -> list[Document]:
        stmt = (
            select(Document)
            .where(documents_table.c.shift_id == shift_id)
            .order_by(documents_table.c.created_at.asc())
        )
        return list((await self._session.execute(stmt)).scalars().all())


class SqlAlchemyResourceRequestRepository(
    SqlAlchemyRepository[ShiftResourceRequest], ResourceRequestRepository
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ShiftResourceRequest)

    async def list_by_shift(self, shift_id: UUID) -> list[ShiftResourceRequest]:
        stmt = select(ShiftResourceRequest).where(
            ShiftResourceRequest.shift_id == shift_id
        )
        return list((await self._session.execute(stmt)).scalars().all())


class SqlAlchemyShiftReportRepository(SqlAlchemyRepository[ShiftReport], ShiftReportRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ShiftReport)

    async def list_by_shift(self, shift_id: UUID) -> list[ShiftReport]:
        stmt = (
            select(ShiftReport)
            .where(shift_reports_table.c.shift_id == shift_id)
            .order_by(shift_reports_table.c.version.desc())
        )
        return list((await self._session.execute(stmt)).scalars().all())


class SqlAlchemyReservationOutboxRepository(ReservationOutboxRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, message: ReservationOutboxMessage) -> None:
        self._session.add(message)

    async def get_by_id(self, message_id: UUID) -> ReservationOutboxMessage | None:
        return await self._session.get(ReservationOutboxMessage, message_id)

    async def list_pending(self, *, limit: int) -> list[ReservationOutboxMessage]:
        stmt = (
            select(ReservationOutboxMessage)
            .where(reservation_outbox.c.status == "pending")
            .order_by(reservation_outbox.c.created_at.asc())
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def update(self, message: ReservationOutboxMessage) -> None:
        self._session.add(message)
