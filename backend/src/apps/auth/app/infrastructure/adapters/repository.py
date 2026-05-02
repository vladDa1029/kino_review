import abc
from typing import Generic, Protocol, Sequence, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.common.filters import Filter
from app.application.common.pagination import Pagination
from app.application.common.sorting import Sorting
from app.application.errors.query_param import SortingError
from app.domain import entities
from app.domain.values import Email

T = TypeVar("T", bound=entities.Base)


class UserAbstractRepository(Protocol, Generic[T]):
    @abc.abstractmethod
    async def add(self, entity: T):
        raise NotImplementedError

    @abc.abstractmethod
    async def get(self, reference) -> T | None:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_by_email(self, email) -> T | None:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_by_username(self, username: str) -> T | None:
        raise NotImplementedError

    @abc.abstractmethod
    async def list(
        self,
        filters: Filter | None = None,
        sorting: Sorting | None = None,
        pagination: Pagination | None = None,
    ) -> Sequence[T]:
        raise NotImplementedError

    @abc.abstractmethod
    async def delete(self, entity: T) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def count(self, filters: Filter | None = None) -> int:
        raise NotImplementedError


def _apply_equipment_filters(stmt, model: type[T], filters: Filter | None):
    if filters is None:
        return stmt
    if filters.base_id is not None:
        stmt = stmt.where(model.oid == filters.base_id)
    if filters.created_from is not None:
        stmt = stmt.where(model.create_at >= filters.created_from)
    if filters.created_to is not None:
        stmt = stmt.where(model.create_at <= filters.created_to)
    if filters.search is not None:
        pattern = f"%{filters.search}%"
        stmt = stmt.where(model.email.ilike(pattern))
    return stmt


def _apply_equipment_sorting(stmt, model: type[T], sorting: Sorting | None):
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


class UserSqlAlchemyRepository(UserAbstractRepository[entities.User]):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, entity: entities.User):
        self.session.add(entity)

    async def delete(self, entity: entities.User) -> None:
        await self.session.delete(entity)

    async def get(self, oid) -> entities.User | None:
        result = await self.session.execute(
            select(entities.User).where(entities.User.oid == oid)
        )
        return result.scalars().first()

    async def get_by_email(self, email: Email) -> entities.User | None:
        result = await self.session.execute(
            select(entities.User).where(entities.User.email == email)
        )
        return result.scalars().first()

    async def get_by_username(self, username: str) -> entities.User | None:
        result = await self.session.execute(
            select(entities.User).where(entities.User.username == username)
        )
        return result.scalars().first()

    # todo:  нетт поддержки фильров и не хватает скорости в больших данных (2 не скоро )
    async def list(
        self,
        filters: Filter | None = None,
        sorting: Sorting | None = None,
        pagination: Pagination | None = None,
    ) -> Sequence[entities.User]:
        stmt = select(entities.User)
        stmt = _apply_equipment_filters(stmt, entities.User, filters)
        stmt = _apply_equipment_sorting(stmt, entities.User, sorting)
        stmt = _apply_pagination(stmt, pagination)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(self, filters: Filter | None = None) -> int:
        count_stmt = select(func.count(entities.User.oid)).select_from(entities.User)
        count_stmt = _apply_equipment_filters(count_stmt, entities.User, filters)
        count_res = await self.session.execute(count_stmt)
        return count_res.scalar_one()
