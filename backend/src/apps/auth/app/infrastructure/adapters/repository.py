import abc
from typing import Generic, Protocol, Sequence, TypeVar
from app.domain import entities
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
    async def list(self) -> Sequence[T]:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_by_email(self, email) -> T | None:
        raise NotImplemented

    @abc.abstractmethod
    async def get_by_username(self, username: str) -> T | None:
        raise NotImplemented


class UserSqlAlchemyRepository(UserAbstractRepository[entities.User]):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, entity: entities.User):
        self.session.add(entity)

    async def get(self, oid):
        result = await self.session.execute(
            select(entities.User).where(entities.User.oid == oid)
        )
        return result.scalars().first()

    async def get_by_email(self, email:Email) -> entities.User | None:
        result = await self.session.execute(
            select(entities.User).where(entities.User.email == email)
        )
        return result.scalars().first()

    async def get_by_username(self, username: str) -> entities.User | None:
        result = await self.session.execute(
            select(entities.User).where(entities.User.username == username)
        )
        return result.scalars().first()

    async def list(self) -> Sequence[entities.User]:
        result = await self.session.execute(select(entities.User))
        return result.scalars().all()
