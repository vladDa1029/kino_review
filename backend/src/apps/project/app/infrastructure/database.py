from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import DatabaseSettings, SQLAlchemySettings


async def get_engine(
    settings: DatabaseSettings, alchemy: SQLAlchemySettings
) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(
        settings.url,
        echo=alchemy.echo,
        echo_pool=alchemy.echo_pool,
        pool_size=alchemy.pool_size,
        max_overflow=alchemy.max_overflow,
        pool_timeout=alchemy.pool_timeout,
        pool_recycle=alchemy.pool_recycle,
        pool_pre_ping=alchemy.pool_pre_ping,
    )
    yield engine
    await engine.dispose()


def get_sessionmaker(
    engine: AsyncEngine, alchemy: SQLAlchemySettings
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=engine,
        autoflush=alchemy.auto_flush,
        expire_on_commit=alchemy.expire_on_commit,
    )


async def get_session(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with sessionmaker() as session:
        yield session


async def create_schema(engine: AsyncEngine) -> None:
    from app.infrastructure.adapters.orm import metadata

    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
