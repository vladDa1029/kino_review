from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from structlog import getLogger

from app.application.ports.repositories import UserRepository
from app.application.ports.transaction import TransactionManager
from app.domain.entity.base import BaseId, User
from app.domain.value.email import Email
from app.infrastructure.generation import AbstractGenerationID

log = getLogger(__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class UserRegisteredCommand:
    email: str
    is_active: bool
    is_superuser: bool
    is_verified: bool
    create_at: datetime
    user_id: UUID


class UserRegisteredHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        transaction: TransactionManager,
        id_generator: AbstractGenerationID,
    ) -> None:
        self._user_repository = user_repository
        self._transaction = transaction
        self._id_generator = id_generator

    async def __call__(self, command: UserRegisteredCommand) -> None:
        try:
            existing = await self._user_repository.get_by_email(Email(command.email))
            if existing is None:
                oid = (
                    BaseId(command.user_id)
                    if command.user_id is not None
                    else self._id_generator()
                )
                log.debug(
                    f"Полученное id от другого сервиса/записанное: {command.user_id} / {oid} ."
                )
                user = User(
                    oid=oid,
                    email=Email(command.email),
                    is_active=command.is_active,
                    is_superuser=command.is_superuser,
                    is_verified=command.is_verified,
                    create_at=command.create_at,
                )
                await self._user_repository.add(user)
            else:
                existing.is_active = command.is_active
                existing.is_superuser = command.is_superuser
                existing.is_verified = command.is_verified
                await self._user_repository.update(existing)
            await self._transaction.commit()
        except Exception:
            await self._transaction.rollback()
            raise
