from typing import Final

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.transaction import TransactionManager
from app.infrastructure.constants import DB_COMMIT_FAILED, DB_ROLLBACK_FAILED
from app.infrastructure.errors.transactions import CommitError, RollbackError


class TransactionManagerAlchemy(TransactionManager):
    """SQLAlchemy implementation of the transaction interface."""

    def __init__(self, session: AsyncSession) -> None:
        self._session: Final[AsyncSession] = session

    async def commit(self) -> None:
        try:
            await self._session.commit()
        except SQLAlchemyError as err:
            raise CommitError(DB_COMMIT_FAILED) from err

    async def rollback(self) -> None:
        try:
            await self._session.rollback()
        except SQLAlchemyError as err:
            raise RollbackError(DB_ROLLBACK_FAILED) from err
