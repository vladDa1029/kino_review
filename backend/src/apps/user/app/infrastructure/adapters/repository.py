from typing import Any, Generic, TypeVar

from sqlalchemy import Column, Table, delete, func, insert, or_, select, update
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
from app.domain.value.status import AvailabilityStatus
from app.infrastructure.adapters.orm import (
    camera_free_times,
    camera_tripod_free_times,
    light_free_times,
    light_tripod_free_times,
    microfon_free_times,
    requisite_free_times,
    sound_free_times,
)

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


class SqlAlchemyFreeTimeRepository(Repository[Spare_time]):
    def __init__(self, session: AsyncSession, table: Table, obj_column: Column) -> None:
        self._session = session
        self._table = table
        self._obj_column = obj_column

    def _row_to_entity(self, row) -> Spare_time:
        return Spare_time(
            oid=BaseId(row["oid"]),
            obj=BaseId(row[self._obj_column.name]),
            start_time=row["start_time"],
            end_time=row["end_time"],
            status=AvailabilityStatus(row["status"]),
        )

    async def add(self, entity: Spare_time) -> None:
        values = {
            "oid": entity.oid,
            self._obj_column.name: entity.obj,
            "start_time": entity.start_time,
            "end_time": entity.end_time,
            "status": str(entity.status),
        }
        await self._session.execute(insert(self._table).values(**values))

    async def get(self, reference: Any) -> Spare_time | None:
        stmt = select(self._table).where(self._table.c.oid == reference)
        result = await self._session.execute(stmt)
        row = result.mappings().first()
        if row is None:
            return None
        return self._row_to_entity(row)

    async def update(self, entity: Spare_time) -> None:
        values = {
            self._obj_column.name: entity.obj,
            "start_time": entity.start_time,
            "end_time": entity.end_time,
            "status": str(entity.status),
        }
        stmt = (
            update(self._table)
            .where(self._table.c.oid == entity.oid)
            .values(**values)
        )
        await self._session.execute(stmt)

    async def delete(self, entity: Spare_time) -> None:
        stmt = delete(self._table).where(self._table.c.oid == entity.oid)
        await self._session.execute(stmt)

    async def list_by_obj_id(self, obj_id: BaseId) -> list[Spare_time]:
        stmt = select(self._table).where(self._obj_column == obj_id)
        result = await self._session.execute(stmt)
        return [self._row_to_entity(row) for row in result.mappings().all()]


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


class MicrofonFreeTimeSqlAlchemyRepository(SqlAlchemyFreeTimeRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, microfon_free_times, microfon_free_times.c.microfon_id)


class CameraSqlAlchemyRepository(SqlAlchemyEquipmentRepository[Camera]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Camera)


class CameraFreeTimeSqlAlchemyRepository(SqlAlchemyFreeTimeRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, camera_free_times, camera_free_times.c.camera_id)


class CameraTripodSqlAlchemyRepository(SqlAlchemyEquipmentRepository[CameraTripod]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CameraTripod)


class CameraTripodFreeTimeSqlAlchemyRepository(SqlAlchemyFreeTimeRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(
            session,
            camera_tripod_free_times,
            camera_tripod_free_times.c.camera_tripod_id,
        )


class LightSqlAlchemyRepository(SqlAlchemyEquipmentRepository[Light]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Light)


class LightFreeTimeSqlAlchemyRepository(SqlAlchemyFreeTimeRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, light_free_times, light_free_times.c.light_id)


class LightTripodSqlAlchemyRepository(SqlAlchemyEquipmentRepository[LightTripod]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, LightTripod)


class LightTripodFreeTimeSqlAlchemyRepository(SqlAlchemyFreeTimeRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(
            session,
            light_tripod_free_times,
            light_tripod_free_times.c.light_tripod_id,
        )


class SoundSqlAlchemyRepository(SqlAlchemyEquipmentRepository[Sound]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Sound)


class SoundFreeTimeSqlAlchemyRepository(SqlAlchemyFreeTimeRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, sound_free_times, sound_free_times.c.sound_id)


class RequisiteSqlAlchemyRepository(SqlAlchemyEquipmentRepository[Requisite]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Requisite)


class RequisiteFreeTimeSqlAlchemyRepository(SqlAlchemyFreeTimeRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(
            session,
            requisite_free_times,
            requisite_free_times.c.requisite_id,
        )


class ImageSqlAlchemyRepository(SqlAlchemyRepository[Image]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Image)

    async def list_by_requisite_id(self, requisite_id: BaseId) -> list[Image]:
        stmt = select(Image).where(Image.requisite_id == requisite_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
