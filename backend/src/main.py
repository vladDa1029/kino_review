from logging import getLogger
from typing import Any
from fastapi_users import FastAPIUsers

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from src.db import database_session
from src.settings.loger import set_log
from src.users.manager import get_user_manager
from src.users.models import User
from src.users.schemas import UserCreate, UserRead
from src.users.strategy import auth_backend

set_log()

app = FastAPI()
log = getLogger(__name__)


@app.get("/", tags=["dev"], description="Проверка, а не не проверка")
async def hell_word() -> dict[str, str]:
    return {"message": "hello word"}


@app.get(
    "/test_connect",
    tags=["dev"],
    description="Проверка подключения к БД",
    summary="Важно",
)
async def test_work_db(
    session: AsyncSession = Depends(database_session.session_dependency),
) -> dict[str, Any]:

    await session.connection()
    return {"status": "Database connection established"}


@app.get("/test_request", tags=["dev"], description="Проверка на запросы в БД")
async def test_request(
    session: AsyncSession = Depends(database_session.session_dependency),
) -> dict[str, Any | None]:
    result = await session.execute(text("SELECT 1"))
    current_result = result.scalars().first()
    return {"message": current_result}


fastapi_users = FastAPIUsers[User, int](get_user_manager, [auth_backend])

current_active_user = fastapi_users.current_user(active=True)


app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)

app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"],
)
origins = [
    "http://localhost.tiangolo.com",
    "https://localhost.tiangolo.com",
    "http://localhost",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
