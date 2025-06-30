from fastapi import Depends
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession
from src.db import database_session
from src.users.models import User


async def get_user_db(
    session: AsyncSession = Depends(database_session.session_dependency),
):
    yield SQLAlchemyUserDatabase(session, User)
