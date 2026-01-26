from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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


class UserSqlAlchemyRepository(SqlAlchemyRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)


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


class MicrofonSqlAlchemyRepository(SqlAlchemyRepository[Microfon]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Microfon)


class CameraSqlAlchemyRepository(SqlAlchemyRepository[Camera]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Camera)


class CameraTripodSqlAlchemyRepository(SqlAlchemyRepository[CameraTripod]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CameraTripod)


class LightSqlAlchemyRepository(SqlAlchemyRepository[Light]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Light)


class LightTripodSqlAlchemyRepository(SqlAlchemyRepository[LightTripod]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, LightTripod)


class SoundSqlAlchemyRepository(SqlAlchemyRepository[Sound]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Sound)


class RequisiteSqlAlchemyRepository(SqlAlchemyRepository[Requisite]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Requisite)


class ImageSqlAlchemyRepository(SqlAlchemyRepository[Image]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Image)

    async def list_by_requisite_id(self, requisite_id: BaseId) -> list[Image]:
        stmt = select(Image).where(Image.requisite_id == requisite_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
