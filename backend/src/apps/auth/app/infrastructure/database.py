from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

# TODO: Доделать прокидывание настроек


settings = get_settings()

engine = create_async_engine(
    url=settings.db.url,
    echo=True,
)
session_factory = async_sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
    autocommit=False,
)


async def get_session():
    async with session_factory() as session:
        yield session


SesDep = Annotated[AsyncSession, Depends(get_session)]
