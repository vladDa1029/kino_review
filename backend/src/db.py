# TODO: refactor code.  not DIP

from typing import Annotated, Any, AsyncGenerator, Generator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.settings.config import Settings, get_settings


class DatabaseManager:
    def __init__(self, settings: Settings):
        self.engine = create_async_engine(url=settings.db.url, echo=True)
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
            autocommit=False,
        )

    async def session_dependency(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.session_factory.begin() as session:

            yield session

    async def session_dependensy_users(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.session_factory() as session:
            yield session


db_manager = DatabaseManager(settings=get_settings())
DbDep = Annotated[AsyncSession, Depends(db_manager.session_dependency)]
DbUsersDep = Annotated[AsyncSession, Depends(db_manager.session_dependensy_users)]
