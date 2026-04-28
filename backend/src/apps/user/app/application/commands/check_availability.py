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
from app.domain.service.availability_service import AvailabilityService


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
        service: AvailabilityService,
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
        self._service = service

    async def __call__(self, command: CheckAvailabilityCommand) -> None:
        user = await self._user_repository.get(command.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")
        await self._resource_ownership.ensure_owned_by_user(
            user_id=command.user_id,
            obj_id=command.obj_id,
        )

        _, windows = await self._resolve_free_time_repository(command.obj_id)
        # Check phase must be side-effect free, so validation runs on a detached list copy.
        self._service.reserve(
            user,
            list(windows),
            command.owner_id,
            command.obj_id,
            command.start_time,
            command.end_time,
        )

    async def _resolve_free_time_repository(
        self, obj_id: BaseId
    ) -> tuple[FreeTimeRepository, list[Spare_time]]:
        for repository in self._free_time_repositories:
            windows = await repository.list_by_obj_id(obj_id)
            if windows:
                return repository, windows
        return self._spare_time_repository, []
