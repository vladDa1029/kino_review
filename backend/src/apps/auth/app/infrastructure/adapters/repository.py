import abc
from typing import Generic, Sequence, TypeVar
from unittest.mock import Base
from app.domain import entities
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T", bound=Base)

# TODO: Возможно стоит воспользоваться Protocol.
class AbstractRepository(abc.ABC, Generic[T]):
    @abc.abstractmethod
    async def add(self, entity: T):
        raise NotImplementedError

    @abc.abstractmethod
    async def get(self, reference) -> T | None:
        raise NotImplementedError

    @abc.abstractmethod
    async def list(self) -> Sequence[T]:
        raise NotImplementedError


class UserSqlAlchemyRepository(AbstractRepository[entities.User]):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, entity: entities.User):
        self.session.add(entity)

    async def get(self, oid):
        result = await self.session.execute(
            select(entities.User).where(entities.User.oid == oid)
        )
        return result.scalars().first()

    async def get_by_email(self, email:str) -> entities.User | None:
        result = await self.session.execute(
            select(entities.User).where(entities.User.email == email)
        )
        return result.scalars().first()

    async def list(self) -> Sequence[entities.User]:
        result = await self.session.execute(select(entities.User))
        return result.scalars().all()

class TokenRepository(abc.ABC):
    ...    
