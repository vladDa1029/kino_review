from dataclasses import dataclass
from datetime import datetime

from app.application.errors.errors import EntityNotFoundError, UserNotFoundError
from app.application.ports.repositories import SpareTimeRepository, UserRepository
from app.application.ports.transaction import TransactionManager
from app.domain.entity.base import BaseId, Spare_time
from app.domain.errors.policy import ResourceLockedError
from app.domain.service.free_time_service import FreeTimeService


@dataclass(frozen=True, slots=True, kw_only=True)
class UpdateSpareTimeCommand:
    user_id: BaseId
    spare_time_id: BaseId
    start_time: datetime
    end_time: datetime


class UpdateSpareTimeHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        spare_time_repository: SpareTimeRepository,
        transaction: TransactionManager,
        service: FreeTimeService,
    ) -> None:
        self._user_repository = user_repository
        self._spare_time_repository = spare_time_repository
        self._transaction = transaction
        self._service = service

    async def __call__(self, command: UpdateSpareTimeCommand) -> None:
        user = await self._user_repository.get(command.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")

        current = await self._spare_time_repository.get(command.spare_time_id)
        if current is None:
            raise EntityNotFoundError("Spare time")

        if str(current.status) != "free":
            raise ResourceLockedError("Spare time is reserved or blocked.")

        timings = await self._spare_time_repository.list_by_obj_id(user.oid)
        timings = [timing for timing in timings if timing.oid != current.oid]
        new_timing = Spare_time(
            oid=current.oid,
            obj=current.obj,
            start_time=command.start_time,
            end_time=command.end_time,
            status=current.status,
        )

        try:
            self._service.add_timing(user, timings, new_timing)
            current.start_time = command.start_time
            current.end_time = command.end_time
            await self._spare_time_repository.update(current)
            await self._transaction.commit()
        except Exception:
            await self._transaction.rollback()
            raise
