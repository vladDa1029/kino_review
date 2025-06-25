# TODO: refactor code.  not DIP

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.settings.config import get_settings

settings = get_settings()


class DatabaseHelper:
    def __init__(self, url: str, echo: bool = False):
        self.engine = create_async_engine(
            url=url,
            echo=echo,
        )
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
            autocommit=False,
        )

    async def session_dependency(self) :
        async with self.session_factory.begin() as session:

            try:
                yield session
            finally:
                await session.close()  # Удаляем сессию после использования


database_session: DatabaseHelper = DatabaseHelper(
    url=settings.db.url,
    echo=True,
)
