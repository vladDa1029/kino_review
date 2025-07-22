import abc
from app.domain import entities
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

class AbstractRepository(abc.ABC):
    @abc.abstractmethod
    async def add(self, user: entities.User):
        raise NotImplementedError

    @abc.abstractmethod
    async def get(self, reference) -> entities.User:
        raise NotImplementedError

    @abc.abstractmethod
    async def list(self):
        raise NotImplementedError

class SqlAlchemyRepository(AbstractRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, user: entities.User):
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)

    async def get(self, reference):
        result = await self.session.execute(
            select(entities.User).where(entities.User.oid == reference)
        )
        return result.scalars().first()

    async def list(self):
        result = await self.session.execute(select(entities.User))
        return result.scalars().all()