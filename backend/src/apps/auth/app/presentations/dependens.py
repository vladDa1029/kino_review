from typing import Annotated

from fastapi import Depends

from app.infrastructure.database import session_factory
from app.services.uow import SqlAlchemyUnitOfWork


def get_user_UoW():
    return SqlAlchemyUnitOfWork(session_factory=session_factory)


UserUoWDep = Annotated[SqlAlchemyUnitOfWork, Depends(get_user_UoW)]
