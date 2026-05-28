from dataclasses import dataclass
from datetime import datetime

from app.application.errors.errors import UserNotFoundError
from app.application.ports.repositories import (
    CameraFreeTimeRepository,
    CameraTripodFreeTimeRepository,
    FreeTimeRepository,
    LightFreeTimeRepository,
    LightTripodFreeTimeRepository,
    MicrofonFreeTimeRepository,
    RequisiteFreeTimeRepository,
    SoundFreeTimeRepository,
    SpareTimeRepository,
    UserRepository,
)
from app.application.resource_ownership import ResourceOwnershipResolver
from app.domain.entity.base import BaseId, Spare_time
from app.domain.errors import ReservationOverlapError
from app.domain.specification.time_overlap import NonOverlappingTimeSpec
from app.domain.value.status import AvailabilityStatus


@dataclass(frozen=True, slots=True, kw_only=True)
class CheckAvailabilityCommand:
    user_id: BaseId
    owner_id: BaseId
    obj_id: BaseId
    start_time: datetime
    end_time: datetime


class CheckAvailabilityHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        spare_time_repository: SpareTimeRepository,
        microfon_free_time_repository: MicrofonFreeTimeRepository,
        camera_free_time_repository: CameraFreeTimeRepository,
        camera_tripod_free_time_repository: CameraTripodFreeTimeRepository,
        light_free_time_repository: LightFreeTimeRepository,
        light_tripod_free_time_repository: LightTripodFreeTimeRepository,
        sound_free_time_repository: SoundFreeTimeRepository,
        requisite_free_time_repository: RequisiteFreeTimeRepository,
        resource_ownership: ResourceOwnershipResolver,
    ) -> None:
        self._user_repository = user_repository
        self._spare_time_repository = spare_time_repository
        self._free_time_repositories: tuple[FreeTimeRepository, ...] = (
            spare_time_repository,
            microfon_free_time_repository,
            camera_free_time_repository,
            camera_tripod_free_time_repository,
            light_free_time_repository,
            light_tripod_free_time_repository,
            sound_free_time_repository,
            requisite_free_time_repository,
        )
        self._resource_ownership = resource_ownership

    async def __call__(self, command: CheckAvailabilityCommand) -> None:
        user = await self._user_repository.get(command.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")
        await self._resource_ownership.ensure_owned_by_user(
            user_id=command.user_id,
            obj_id=command.obj_id,
        )

        # Collect all RESERVED windows for this resource across every free_time
        # table.  A resource can be booked even if it has no FREE windows
        # registered — the absence of FREE slots is not a conflict.
        all_reserved: list[Spare_time] = []
        for repository in self._free_time_repositories:
            windows = await repository.list_by_obj_id(command.obj_id)
            for window in windows:
                if str(window.status) == "reserved":
                    all_reserved.append(window)

        if not all_reserved:
            # No reserved windows exist for this resource — it is free.
            return

        # Build a candidate window that represents the requested interval and
        # check whether it overlaps any already-reserved slot.
        candidate = Spare_time(
            oid=command.obj_id,  # throwaway id — candidate is never persisted
            obj=command.obj_id,
            start_time=command.start_time,
            end_time=command.end_time,
            status=AvailabilityStatus("reserved"),
        )

        spec = NonOverlappingTimeSpec()
        if not spec.is_satisfied(candidate, all_reserved):
            raise ReservationOverlapError(
                "Resource is already reserved for the requested time interval."
            )
