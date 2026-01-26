from dataclasses import dataclass
from datetime import datetime

from app.application.errors.errors import UserNotFoundError
from app.application.ports.repositories import SpareTimeRepository, UserRepository
from app.application.ports.transaction import TransactionManager
from app.domain.entity.base import BaseId
from app.domain.service.availability_service import AvailabilityService
from app.infrastructure.generation import AbstractGenerationID


@dataclass(frozen=True, slots=True, kw_only=True)
class ReserveAvailabilityCommand:
    user_id: BaseId
    owner_id: BaseId
    obj_id: BaseId
    start_time: datetime
    end_time: datetime


class ReserveAvailabilityHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        spare_time_repository: SpareTimeRepository,
        transaction: TransactionManager,
        id_generator: AbstractGenerationID,
        service: AvailabilityService,
    ) -> None:
        self._user_repository = user_repository
        self._spare_time_repository = spare_time_repository
        self._transaction = transaction
        self._id_generator = id_generator
        self._service = service

    async def __call__(self, command: ReserveAvailabilityCommand) -> None:
        user = await self._user_repository.get(command.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")

        windows = await self._spare_time_repository.list_by_obj_id(command.obj_id)
        existing = list(windows)

        try:
            self._service.id_factory = self._id_generator
            result = self._service.reserve(
                user,
                windows,
                command.owner_id,
                command.obj_id,
                command.start_time,
                command.end_time,
            )

            existing_ids = {window.oid for window in existing}
            result_ids = {window.oid for window in result}
            removed = [window for window in existing if window.oid not in result_ids]
            added = [window for window in result if window.oid not in existing_ids]

            for window in removed:
                await self._spare_time_repository.delete(window)
            for window in added:
                await self._spare_time_repository.add(window)

            await self._transaction.commit()
        except Exception:
            await self._transaction.rollback()
            raise
