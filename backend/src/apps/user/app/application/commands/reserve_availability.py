from dataclasses import dataclass
from datetime import datetime

from app.application.errors.errors import UserNotFoundError
from app.application.ports.repositories import (
    AvailabilityReservationRepository,
    CameraFreeTimeRepository,
    CameraRepository,
    CameraTripodFreeTimeRepository,
    CameraTripodRepository,
    FreeTimeRepository,
    LightFreeTimeRepository,
    LightRepository,
    LightTripodFreeTimeRepository,
    LightTripodRepository,
    MicrofonFreeTimeRepository,
    MicrofonRepository,
    RequisiteFreeTimeRepository,
    RequisiteRepository,
    SoundFreeTimeRepository,
    SoundRepository,
    SpareTimeRepository,
    UserRepository,
)
from app.application.ports.transaction import TransactionManager
from app.application.resource_ownership import ResourceOwnershipResolver
from app.domain.entity.base import AvailabilityReservation, BaseId, Spare_time
from app.domain.service.availability_service import AvailabilityService
from app.domain.value.status import AvailabilityStatus
from app.infrastructure.generation import AbstractGenerationID


@dataclass(frozen=True, slots=True, kw_only=True)
class ReserveAvailabilityCommand:
    request_id: BaseId
    user_id: BaseId
    owner_id: BaseId
    obj_id: BaseId
    start_time: datetime
    end_time: datetime


class ReserveAvailabilityHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        reservation_repository: AvailabilityReservationRepository,
        spare_time_repository: SpareTimeRepository,
        microfon_free_time_repository: MicrofonFreeTimeRepository,
        camera_free_time_repository: CameraFreeTimeRepository,
        camera_tripod_free_time_repository: CameraTripodFreeTimeRepository,
        light_free_time_repository: LightFreeTimeRepository,
        light_tripod_free_time_repository: LightTripodFreeTimeRepository,
        sound_free_time_repository: SoundFreeTimeRepository,
        requisite_free_time_repository: RequisiteFreeTimeRepository,
        microfon_repository: MicrofonRepository,
        camera_repository: CameraRepository,
        camera_tripod_repository: CameraTripodRepository,
        light_repository: LightRepository,
        light_tripod_repository: LightTripodRepository,
        sound_repository: SoundRepository,
        requisite_repository: RequisiteRepository,
        transaction: TransactionManager,
        id_generator: AbstractGenerationID,
        resource_ownership: ResourceOwnershipResolver,
        service: AvailabilityService,
    ) -> None:
        self._user_repository = user_repository
        self._reservation_repository = reservation_repository
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
        # Pairs used to find the correct free_time table when no windows are
        # pre-registered: look up the equipment row, then write to that repo.
        self._repo_pairs: tuple[tuple, ...] = (
            (microfon_repository, microfon_free_time_repository),
            (camera_repository, camera_free_time_repository),
            (camera_tripod_repository, camera_tripod_free_time_repository),
            (light_repository, light_free_time_repository),
            (light_tripod_repository, light_tripod_free_time_repository),
            (sound_repository, sound_free_time_repository),
            (requisite_repository, requisite_free_time_repository),
        )
        self._transaction = transaction
        self._id_generator = id_generator
        self._resource_ownership = resource_ownership
        self._service = service

    async def __call__(self, command: ReserveAvailabilityCommand) -> BaseId:
        existing_reservation = await self._reservation_repository.get(command.request_id)
        if existing_reservation is not None:
            if (
                existing_reservation.user_id != command.user_id
                or existing_reservation.obj_id != command.obj_id
                or existing_reservation.start_time != command.start_time
                or existing_reservation.end_time != command.end_time
            ):
                raise ValueError("request_id already used with a different reserve payload.")
            return existing_reservation.reservation_id

        user = await self._user_repository.get(command.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")
        await self._resource_ownership.ensure_owned_by_user(
            user_id=command.user_id,
            obj_id=command.obj_id,
        )

        free_time_repository, windows = await self._resolve_free_time_repository(
            command.obj_id
        )

        if not windows:
            # Resource has no pre-registered free_time windows.
            # Find the correct equipment free_time table and create the
            # "reserved" entry directly — no splitting required.
            free_time_repository = await self._find_equipment_free_time_repo(
                command.obj_id, fallback=free_time_repository
            )
            reservation_id = BaseId(self._id_generator())
            reserved_window = Spare_time(
                oid=reservation_id,
                obj=command.obj_id,
                start_time=command.start_time,
                end_time=command.end_time,
                status=AvailabilityStatus("reserved"),
            )
            try:
                await free_time_repository.add(reserved_window)
                await self._reservation_repository.add(
                    AvailabilityReservation(
                        oid=command.request_id,
                        user_id=command.user_id,
                        obj_id=command.obj_id,
                        start_time=command.start_time,
                        end_time=command.end_time,
                        reservation_id=reservation_id,
                        created_at=datetime.now(tz=command.start_time.tzinfo),
                    )
                )
                await self._transaction.commit()
            except Exception:
                await self._transaction.rollback()
                raise
            return reservation_id

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
                await free_time_repository.delete(window)
            for window in added:
                await free_time_repository.add(window)
            reservation = next(
                (
                    window
                    for window in added
                    if window.obj == command.obj_id
                    and window.start_time == command.start_time
                    and window.end_time == command.end_time
                    and str(window.status) == "reserved"
                ),
                None,
            )
            if reservation is None:
                raise RuntimeError("Reserved availability window was not created.")
            await self._reservation_repository.add(
                AvailabilityReservation(
                    oid=command.request_id,
                    user_id=command.user_id,
                    obj_id=command.obj_id,
                    start_time=command.start_time,
                    end_time=command.end_time,
                    reservation_id=reservation.oid,
                    created_at=datetime.now(tz=command.start_time.tzinfo),
                )
            )
            await self._transaction.commit()
            return reservation.oid
        except Exception:
            await self._transaction.rollback()
            raise

    async def _resolve_free_time_repository(
        self, obj_id: BaseId
    ) -> tuple[FreeTimeRepository, list[Spare_time]]:
        for repository in self._free_time_repositories:
            windows = await repository.list_by_obj_id(obj_id)
            if windows:
                return repository, windows
        return self._spare_time_repository, []

    async def _find_equipment_free_time_repo(
        self,
        obj_id: BaseId,
        fallback: FreeTimeRepository,
    ) -> FreeTimeRepository:
        """Return the correct free_time repository for an equipment resource.

        Tries each equipment repository in turn; when the resource row is found
        the paired free_time repository is returned.  Falls back to *fallback*
        (typically spare_time_repository for user-owned resources) when the
        resource does not belong to any known equipment table.
        """
        for equipment_repo, free_time_repo in self._repo_pairs:
            if await equipment_repo.get(obj_id) is not None:
                return free_time_repo
        return fallback
