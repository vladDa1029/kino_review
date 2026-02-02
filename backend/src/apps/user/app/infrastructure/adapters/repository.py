from typing import Any, Generic, TypeVar

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.common.filters import EquipmentFilters
from app.application.common.pagination import Pagination
from app.application.common.sorting import EquipmentSorting
from app.application.errors.query_param import FilterError, SortingError
from app.application.ports.repository import Repository
from app.domain.entity.base import (
    BaseId,
    Camera,
    CameraTripod,
    Description,
    Image,
    Light,
    LightTripod,
    Microfon,
    Requisite,
    Sound,
    Spare_time,
    User,
)
from app.domain.value.email import Email

T = TypeVar("T")


class SqlAlchemyRepository(Repository[T], Generic[T]):
    """Minimal SQLAlchemy repository for entities with an oid field."""

    def __init__(self, session: AsyncSession, model: type[T]) -> None:
        self._session = session
        self._model = model

    async def add(self, entity: T) -> None:
        self._session.add(entity)

    async def get(self, reference: Any) -> T | None:
        stmt = select(self._model).where(self._model.oid == reference)
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def update(self, entity: T) -> None:
        self._session.add(entity)

    async def delete(self, entity: T) -> None:
        await self._session.delete(entity)


def _apply_equipment_filters(stmt, model: type[T], filters: EquipmentFilters | None):
    if filters is None:
        return stmt
    if filters.user_id is not None:
        stmt = stmt.where(model.users_id == filters.user_id)
    if filters.type is not None:
        stmt = stmt.where(model.type == filters.type)
    if filters.size is not None:
        if not hasattr(model, "size"):
            raise FilterError("size filter is not supported for this resource.")
        stmt = stmt.where(model.size == filters.size)
    if filters.created_from is not None:
        stmt = stmt.where(model.create_at >= filters.created_from)
    if filters.created_to is not None:
        stmt = stmt.where(model.create_at <= filters.created_to)
    if filters.search is not None:
        pattern = f"%{filters.search}%"
        stmt = stmt.where(
            or_(model.title.ilike(pattern), model.description.ilike(pattern))
        )
    return stmt


def _apply_equipment_sorting(
    stmt, model: type[T], sorting: EquipmentSorting | None
):
    if sorting is None:
        return stmt
    column = getattr(model, sorting.field, None)
    if column is None:
        raise SortingError(f"sort field '{sorting.field}' is not supported.")
    if sorting.direction == "desc":
        return stmt.order_by(column.desc())
    return stmt.order_by(column.asc())


def _apply_pagination(stmt, pagination: Pagination | None):
    if pagination is None:
        return stmt
    return stmt.limit(pagination.limit).offset(pagination.offset)


class SqlAlchemyEquipmentRepository(SqlAlchemyRepository[T], Generic[T]):
    async def list(
        self,
        filters: EquipmentFilters | None = None,
        sorting: EquipmentSorting | None = None,
        pagination: Pagination | None = None,
    ) -> list[T]:
        stmt = select(self._model)
        stmt = _apply_equipment_filters(stmt, self._model, filters)
        stmt = _apply_equipment_sorting(stmt, self._model, sorting)
        stmt = _apply_pagination(stmt, pagination)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count(
        self,
        filters: EquipmentFilters | None = None,
    ) -> int:
        stmt = select(func.count(self._model.oid)).select_from(self._model)
        stmt = _apply_equipment_filters(stmt, self._model, filters)
        result = await self._session.execute(stmt)
        return int(result.scalar_one())


class UserSqlAlchemyRepository(SqlAlchemyRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)

    async def get_by_email(self, email: Email) -> User | None:
        stmt = select(User).where(User.email == email)
        result = await self._session.execute(stmt)
        return result.scalars().first()


class DescriptionSqlAlchemyRepository(SqlAlchemyRepository[Description]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Description)

    async def get_by_user_id(self, user_id: BaseId) -> Description | None:
        stmt = select(Description).where(Description.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.scalars().first()


class SpareTimeSqlAlchemyRepository(SqlAlchemyRepository[Spare_time]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Spare_time)

    async def list_by_obj_id(self, obj_id: BaseId) -> list[Spare_time]:
        stmt = select(Spare_time).where(Spare_time.obj == obj_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class MicrofonSqlAlchemyRepository(SqlAlchemyEquipmentRepository[Microfon]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Microfon)


class CameraSqlAlchemyRepository(SqlAlchemyEquipmentRepository[Camera]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Camera)


class CameraTripodSqlAlchemyRepository(SqlAlchemyEquipmentRepository[CameraTripod]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CameraTripod)


class LightSqlAlchemyRepository(SqlAlchemyEquipmentRepository[Light]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Light)


class LightTripodSqlAlchemyRepository(SqlAlchemyEquipmentRepository[LightTripod]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, LightTripod)


class SoundSqlAlchemyRepository(SqlAlchemyEquipmentRepository[Sound]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Sound)


class RequisiteSqlAlchemyRepository(SqlAlchemyEquipmentRepository[Requisite]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Requisite)


class ImageSqlAlchemyRepository(SqlAlchemyRepository[Image]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Image)

    async def list_by_requisite_id(self, requisite_id: BaseId) -> list[Image]:
        stmt = select(Image).where(Image.requisite_id == requisite_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
