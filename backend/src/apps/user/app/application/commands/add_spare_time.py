from dataclasses import dataclass
from datetime import datetime

from app.application.errors.errors import UserNotFoundError
from app.application.ports.repositories import SpareTimeRepository, UserRepository
from app.application.ports.transaction import TransactionManager
from app.domain.entity.base import BaseId, Spare_time
from app.domain.service.free_time_service import FreeTimeService
from app.infrastructure.generation import AbstractGenerationID


@dataclass(frozen=True, slots=True, kw_only=True)
class AddSpareTimeCommand:
    user_id: BaseId
    start_time: datetime
    end_time: datetime


class AddSpareTimeHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        spare_time_repository: SpareTimeRepository,
        transaction: TransactionManager,
        id_generator: AbstractGenerationID,
        service: FreeTimeService,
    ) -> None:
        self._user_repository = user_repository
        self._spare_time_repository = spare_time_repository
        self._transaction = transaction
        self._id_generator = id_generator
        self._service = service

    async def __call__(self, command: AddSpareTimeCommand) -> None:
        user = await self._user_repository.get(command.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")

        timings = await self._spare_time_repository.list_by_obj_id(user.oid)
        new_timing = Spare_time(
            oid=self._id_generator(),
            obj=user.oid,
            start_time=command.start_time,
            end_time=command.end_time,
        )

        try:
            self._service.add_timing(user, timings, new_timing)
            await self._spare_time_repository.add(new_timing)
            await self._transaction.commit()
        except Exception:
            await self._transaction.rollback()
            raise
