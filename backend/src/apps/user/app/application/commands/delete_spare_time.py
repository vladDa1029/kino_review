from dataclasses import dataclass

from app.application.errors.errors import EntityNotFoundError, UserNotFoundError
from app.application.ports.repositories import SpareTimeRepository, UserRepository
from app.application.ports.transaction import TransactionManager
from app.domain.entity.base import BaseId
from app.domain.errors.policy import ResourceLockedError
from app.domain.policy.active_user import ActiveUserPolicy
from app.domain.policy.ownership import OwnershipPolicy


@dataclass(frozen=True, slots=True, kw_only=True)
class DeleteSpareTimeCommand:
    user_id: BaseId
    spare_time_id: BaseId


class DeleteSpareTimeHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        spare_time_repository: SpareTimeRepository,
        transaction: TransactionManager,
        active_user_policy: ActiveUserPolicy,
        ownership_policy: OwnershipPolicy,
    ) -> None:
        self._user_repository = user_repository
        self._spare_time_repository = spare_time_repository
        self._transaction = transaction
        self._active_user_policy = active_user_policy
        self._ownership_policy = ownership_policy

    async def __call__(self, command: DeleteSpareTimeCommand) -> None:
        user = await self._user_repository.get(command.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")

        current = await self._spare_time_repository.get(command.spare_time_id)
        if current is None:
            raise EntityNotFoundError("Spare time")

        if str(current.status) != "free":
            raise ResourceLockedError("Spare time is reserved or blocked.")

        self._active_user_policy.check(user)
        self._ownership_policy.check(user.oid, current.obj)

        try:
            await self._spare_time_repository.delete(current)
            await self._transaction.commit()
        except Exception:
            await self._transaction.rollback()
            raise
