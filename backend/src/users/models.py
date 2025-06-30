from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTable
from sqlalchemy.orm import Mapped, mapped_column

from src.core.domain.base import Base


class User(Base, SQLAlchemyBaseUserTable[int]):
    id: Mapped[int] = mapped_column(primary_key=True)
    