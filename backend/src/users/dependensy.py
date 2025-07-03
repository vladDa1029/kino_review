from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from src.db import DbUsersDep
from src.users.models import User


async def get_user_db(
    session: DbUsersDep,
):
    yield SQLAlchemyUserDatabase(session, User)
