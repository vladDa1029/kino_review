from typing import Final
from typing_extensions import override

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.infrastruct import TransactionManager

from app.infrastructure.exaptions.transactions import (
    CommitExaption,
    RollbackExaption,
)


class TransactionManagerAlchemy(TransactionManager):
    """SQLAlchemy implementation of the Transaction interface.

    Provides asynchronous transaction management using SQLAlchemy's session,
    handling commit and flush operations for atomic changes.

    Args:
        session: Async SQLAlchemy session to manage transactions for.

    Note:
        - Wraps SQLAlchemy's async transaction methods
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initializes the transaction manager with a database session.

        Args:
            session: Async SQLAlchemy session for transaction operations.
        """
        self._session: Final[AsyncSession] = session

    @override
    async def commit(self) -> None:
        """Commits all pending changes to the database.

        Note:
            - Makes all staged changes permanent
            - Ends the current transaction
            - Raises if any conflicts or violations occur
            - Starts a new transaction automatically
        """
        try:
            await self._session.commit()
        except SQLAlchemyError as err:
            raise CommitExaption from err

    @override
    async def rollback(self) -> None:
        """Flushes pending changes without committing.

        Note:
            - Writes changes to database but doesn't commit
            - Useful for getting generated IDs before commit
            - Maintains transaction isolation
        """
        try:
            await self._session.rollback()
        except SQLAlchemyError as err:
            raise RollbackExaption from err



    