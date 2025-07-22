from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from config import get_settings
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