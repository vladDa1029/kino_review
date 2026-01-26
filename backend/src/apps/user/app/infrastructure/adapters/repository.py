from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.repository import Repository

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
