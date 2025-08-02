from typing import Annotated

from fastapi import Depends

from app.infrastructure.database import session_factory
from app.infrastructure.security.jwt import JWT
from app.infrastructure.adapters.transections import SqlAlchemyUnitOfWork


def get_user_UoW():
    return SqlAlchemyUnitOfWork(session_factory=session_factory)


def get_jwt():
    return JWT()


UserUoWDep = Annotated[SqlAlchemyUnitOfWork, Depends(get_user_UoW)]

JwtDep = Annotated[JWT, Depends(get_jwt)]
