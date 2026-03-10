from dataclasses import dataclass

from app.application.errors.errors import EntityNotFoundError, UserNotFoundError
from app.application.ports.repositories import (
    CameraFreeTimeRepository,
    CameraRepository,
    CameraTripodFreeTimeRepository,
    CameraTripodRepository,
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
    UserRepository,
)
from app.domain.entity.base import BaseId, Spare_time
from app.domain.policy.ownership import OwnershipPolicy


@dataclass(frozen=True, slots=True, kw_only=True)
class ListMicrofonFreeTimesQuery:
    user_id: BaseId
    microfon_id: BaseId


@dataclass(frozen=True, slots=True, kw_only=True)
class ListCameraFreeTimesQuery:
    user_id: BaseId
    camera_id: BaseId


@dataclass(frozen=True, slots=True, kw_only=True)
class ListCameraTripodFreeTimesQuery:
    user_id: BaseId
    camera_tripod_id: BaseId


@dataclass(frozen=True, slots=True, kw_only=True)
class ListLightFreeTimesQuery:
    user_id: BaseId
    light_id: BaseId


@dataclass(frozen=True, slots=True, kw_only=True)
class ListLightTripodFreeTimesQuery:
    user_id: BaseId
    light_tripod_id: BaseId


@dataclass(frozen=True, slots=True, kw_only=True)
class ListSoundFreeTimesQuery:
    user_id: BaseId
    sound_id: BaseId


@dataclass(frozen=True, slots=True, kw_only=True)
class ListRequisiteFreeTimesQuery:
    user_id: BaseId
    requisite_id: BaseId


class ListMicrofonFreeTimesHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        microfon_repository: MicrofonRepository,
        microfon_free_time_repository: MicrofonFreeTimeRepository,
        ownership_policy: OwnershipPolicy,
    ) -> None:
        self._user_repository = user_repository
        self._microfon_repository = microfon_repository
        self._microfon_free_time_repository = microfon_free_time_repository
        self._ownership_policy = ownership_policy

    async def __call__(self, query: ListMicrofonFreeTimesQuery) -> list[Spare_time]:
        user = await self._user_repository.get(query.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")
        microfon = await self._microfon_repository.get(query.microfon_id)
        if microfon is None:
            raise EntityNotFoundError("Microfon")
        self._ownership_policy.check(user.oid, microfon.users_id)
        return await self._microfon_free_time_repository.list_by_obj_id(microfon.oid)


class ListCameraFreeTimesHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        camera_repository: CameraRepository,
        camera_free_time_repository: CameraFreeTimeRepository,
        ownership_policy: OwnershipPolicy,
    ) -> None:
        self._user_repository = user_repository
        self._camera_repository = camera_repository
        self._camera_free_time_repository = camera_free_time_repository
        self._ownership_policy = ownership_policy

    async def __call__(self, query: ListCameraFreeTimesQuery) -> list[Spare_time]:
        user = await self._user_repository.get(query.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")
        camera = await self._camera_repository.get(query.camera_id)
        if camera is None:
            raise EntityNotFoundError("Camera")
        self._ownership_policy.check(user.oid, camera.users_id)
        return await self._camera_free_time_repository.list_by_obj_id(camera.oid)


class ListCameraTripodFreeTimesHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        camera_tripod_repository: CameraTripodRepository,
        camera_tripod_free_time_repository: CameraTripodFreeTimeRepository,
        ownership_policy: OwnershipPolicy,
    ) -> None:
        self._user_repository = user_repository
        self._camera_tripod_repository = camera_tripod_repository
        self._camera_tripod_free_time_repository = camera_tripod_free_time_repository
        self._ownership_policy = ownership_policy

    async def __call__(self, query: ListCameraTripodFreeTimesQuery) -> list[Spare_time]:
        user = await self._user_repository.get(query.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")
        camera_tripod = await self._camera_tripod_repository.get(query.camera_tripod_id)
        if camera_tripod is None:
            raise EntityNotFoundError("CameraTripod")
        self._ownership_policy.check(user.oid, camera_tripod.users_id)
        return await self._camera_tripod_free_time_repository.list_by_obj_id(
            camera_tripod.oid
        )


class ListLightFreeTimesHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        light_repository: LightRepository,
        light_free_time_repository: LightFreeTimeRepository,
        ownership_policy: OwnershipPolicy,
    ) -> None:
        self._user_repository = user_repository
        self._light_repository = light_repository
        self._light_free_time_repository = light_free_time_repository
        self._ownership_policy = ownership_policy

    async def __call__(self, query: ListLightFreeTimesQuery) -> list[Spare_time]:
        user = await self._user_repository.get(query.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")
        light = await self._light_repository.get(query.light_id)
        if light is None:
            raise EntityNotFoundError("Light")
        self._ownership_policy.check(user.oid, light.users_id)
        return await self._light_free_time_repository.list_by_obj_id(light.oid)


class ListLightTripodFreeTimesHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        light_tripod_repository: LightTripodRepository,
        light_tripod_free_time_repository: LightTripodFreeTimeRepository,
        ownership_policy: OwnershipPolicy,
    ) -> None:
        self._user_repository = user_repository
        self._light_tripod_repository = light_tripod_repository
        self._light_tripod_free_time_repository = light_tripod_free_time_repository
        self._ownership_policy = ownership_policy

    async def __call__(self, query: ListLightTripodFreeTimesQuery) -> list[Spare_time]:
        user = await self._user_repository.get(query.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")
        light_tripod = await self._light_tripod_repository.get(query.light_tripod_id)
        if light_tripod is None:
            raise EntityNotFoundError("LightTripod")
        self._ownership_policy.check(user.oid, light_tripod.users_id)
        return await self._light_tripod_free_time_repository.list_by_obj_id(
            light_tripod.oid
        )


class ListSoundFreeTimesHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        sound_repository: SoundRepository,
        sound_free_time_repository: SoundFreeTimeRepository,
        ownership_policy: OwnershipPolicy,
    ) -> None:
        self._user_repository = user_repository
        self._sound_repository = sound_repository
        self._sound_free_time_repository = sound_free_time_repository
        self._ownership_policy = ownership_policy

    async def __call__(self, query: ListSoundFreeTimesQuery) -> list[Spare_time]:
        user = await self._user_repository.get(query.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")
        sound = await self._sound_repository.get(query.sound_id)
        if sound is None:
            raise EntityNotFoundError("Sound")
        self._ownership_policy.check(user.oid, sound.users_id)
        return await self._sound_free_time_repository.list_by_obj_id(sound.oid)


class ListRequisiteFreeTimesHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        requisite_repository: RequisiteRepository,
        requisite_free_time_repository: RequisiteFreeTimeRepository,
        ownership_policy: OwnershipPolicy,
    ) -> None:
        self._user_repository = user_repository
        self._requisite_repository = requisite_repository
        self._requisite_free_time_repository = requisite_free_time_repository
        self._ownership_policy = ownership_policy

    async def __call__(self, query: ListRequisiteFreeTimesQuery) -> list[Spare_time]:
        user = await self._user_repository.get(query.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")
        requisite = await self._requisite_repository.get(query.requisite_id)
        if requisite is None:
            raise EntityNotFoundError("Requisite")
        self._ownership_policy.check(user.oid, requisite.users_id)
        return await self._requisite_free_time_repository.list_by_obj_id(requisite.oid)
