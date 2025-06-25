from logging import getLogger
from typing import Any
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from src.db import database_session
from src.settings.loger import set_log

set_log()

app = FastAPI()
log = getLogger(__name__)


@app.get("/", tags=["dev"], description= "Проверка а не не проверка")
async def hell_word() -> dict[str, str]:
    return {"message": "hello word"}


@app.get("/test_connect", tags=["dev"], description= "Проверка подключения к БД", summary='Важно')
async def test_work_db(
    session: AsyncSession = Depends(database_session.session_dependency),
) -> dict[str, Any]:
    try:
        await session.connection()
        return {"status": "Database connection established"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/test_request", tags=["dev"], description="Проверка на запросы в БД")
async def test_request(
    session: AsyncSession = Depends(database_session.session_dependency),
) -> dict[str, Any | None]:
    result = await session.execute(text("SELECT 1"))
    current_result = result.scalars().first()
    return {"message": current_result}


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
