from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from app.application.errors.errors import UserNotFoundError
from app.application.ports.repositories import (
    AvailabilityReservationRepository,
    SpareTimeRepository,
    UserRepository,
)
from app.application.ports.transaction import TransactionManager
from app.domain.entity.base import AvailabilityReservation, BaseId, Spare_time
from app.domain.value.status import AvailabilityStatus


@dataclass(frozen=True, slots=True, kw_only=True)
class ReserveParticipantAvailabilityCommand:
    request_id: BaseId
    user_id: BaseId
    start_time: datetime
    end_time: datetime


class ReserveParticipantAvailabilityHandler:
    """Reserve a participant's time slot directly in free_users_timing.

    Unlike ReserveAvailabilityHandler (used for equipment), participants are
    people who do not pre-register availability windows.  This handler skips
    the free-window lookup and directly inserts a ``status=reserved`` entry
    into ``free_users_timing``, recording the confirmed shift interval so the
    UI can display it as a busy slot.

    Idempotent: if a reservation with the same ``request_id`` already exists
    and its payload matches, the existing ``reservation_id`` is returned.
    """

    def __init__(
        self,
        *,
        user_repository: UserRepository,
        spare_time_repository: SpareTimeRepository,
        reservation_repository: AvailabilityReservationRepository,
        transaction: TransactionManager,
    ) -> None:
        self._users = user_repository
        self._spare_times = spare_time_repository
        self._reservations = reservation_repository
        self._tx = transaction

    async def __call__(
        self,
        command: ReserveParticipantAvailabilityCommand,
    ) -> BaseId:
        # Idempotency: return the existing reservation_id if already committed.
        existing = await self._reservations.get(command.request_id)
        if existing is not None:
            if (
                existing.user_id != command.user_id
                or existing.obj_id != command.user_id
                or existing.start_time != command.start_time
                or existing.end_time != command.end_time
            ):
                raise ValueError(
                    "request_id already used with a different reserve payload."
                )
            return existing.reservation_id

        user = await self._users.get(command.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")

        reservation_id = BaseId(uuid4())
        spare_time_entry = Spare_time(
            oid=reservation_id,
            obj=command.user_id,
            start_time=command.start_time,
            end_time=command.end_time,
            status=AvailabilityStatus("reserved"),
        )

        try:
            await self._spare_times.add(spare_time_entry)
            await self._reservations.add(
                AvailabilityReservation(
                    oid=command.request_id,
                    user_id=command.user_id,
                    obj_id=command.user_id,
                    start_time=command.start_time,
                    end_time=command.end_time,
                    reservation_id=reservation_id,
                    created_at=datetime.now(tz=command.start_time.tzinfo),
                )
            )
            await self._tx.commit()
        except Exception:
            await self._tx.rollback()
            raise

        return reservation_id
