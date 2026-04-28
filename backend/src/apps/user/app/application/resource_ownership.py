from app.application.errors.errors import EntityNotFoundError
from app.application.ports.repositories import (
    CameraRepository,
    CameraTripodRepository,
    EquipmentRepository,
    LightRepository,
    LightTripodRepository,
    MicrofonRepository,
    RequisiteRepository,
    SoundRepository,
)
from app.domain.entity.base import BaseId
from app.domain.policy.ownership import OwnershipPolicy


class ResourceOwnershipResolver:
    def __init__(
        self,
        *,
        microfon_repository: MicrofonRepository,
        camera_repository: CameraRepository,
        camera_tripod_repository: CameraTripodRepository,
        light_repository: LightRepository,
        light_tripod_repository: LightTripodRepository,
        sound_repository: SoundRepository,
        requisite_repository: RequisiteRepository,
        ownership_policy: OwnershipPolicy,
    ) -> None:
        self._repositories: tuple[EquipmentRepository, ...] = (
            microfon_repository,
            camera_repository,
            camera_tripod_repository,
            light_repository,
            light_tripod_repository,
            sound_repository,
            requisite_repository,
        )
        self._ownership_policy = ownership_policy

    async def ensure_owned_by_user(self, *, user_id: BaseId, obj_id: BaseId) -> None:
        if obj_id == user_id:
            return
        for repository in self._repositories:
            resource = await repository.get(obj_id)
            if resource is None:
                continue
            self._ownership_policy.check(user_id, resource.users_id)
            return
        raise EntityNotFoundError("Resource")
