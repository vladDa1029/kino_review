from dataclasses import dataclass

from app.application.errors.errors import EntityNotFoundError, UserNotFoundError
from app.application.ports.repositories import (
    CameraFreeTimeRepository,
    CameraRepository,
    CameraTripodRepository,
    CameraTripodFreeTimeRepository,
    LightRepository,
    LightFreeTimeRepository,
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
from app.application.ports.transaction import TransactionManager
from app.domain.entity.base import BaseId
from app.domain.service.equipment_service import EquipmentService


@dataclass(frozen=True, slots=True, kw_only=True)
class UpdateMicrofonCommand:
    user_id: BaseId
    microfon_id: BaseId
    title: str
    description: str
    type: str


@dataclass(frozen=True, slots=True, kw_only=True)
class UpdateCameraCommand:
    user_id: BaseId
    camera_id: BaseId
    title: str
    description: str
    type: str


@dataclass(frozen=True, slots=True, kw_only=True)
class UpdateCameraTripodCommand:
    user_id: BaseId
    camera_tripod_id: BaseId
    title: str
    description: str
    type: str


@dataclass(frozen=True, slots=True, kw_only=True)
class UpdateLightCommand:
    user_id: BaseId
    light_id: BaseId
    title: str
    description: str
    type: str


@dataclass(frozen=True, slots=True, kw_only=True)
class UpdateLightTripodCommand:
    user_id: BaseId
    light_tripod_id: BaseId
    title: str
    description: str
    type: str


@dataclass(frozen=True, slots=True, kw_only=True)
class UpdateSoundCommand:
    user_id: BaseId
    sound_id: BaseId
    title: str
    description: str
    type: str


@dataclass(frozen=True, slots=True, kw_only=True)
class UpdateRequisiteCommand:
    user_id: BaseId
    requisite_id: BaseId
    title: str
    description: str
    type: str
    size: str


class UpdateMicrofonHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        microfon_repository: MicrofonRepository,
        microfon_free_time_repository: MicrofonFreeTimeRepository,
        transaction: TransactionManager,
        service: EquipmentService,
    ) -> None:
        self._user_repository = user_repository
        self._microfon_repository = microfon_repository
        self._microfon_free_time_repository = microfon_free_time_repository
        self._transaction = transaction
        self._service = service

    async def __call__(self, command: UpdateMicrofonCommand) -> None:
        user = await self._user_repository.get(command.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")

        microfon = await self._microfon_repository.get(command.microfon_id)
        if microfon is None:
            raise EntityNotFoundError("Microfon")

        windows = await self._microfon_free_time_repository.list_by_obj_id(microfon.oid)

        try:
            self._service.update(user, microfon, windows)
            microfon.title = command.title
            microfon.description = command.description
            microfon.type = command.type
            await self._microfon_repository.update(microfon)
            await self._transaction.commit()
        except Exception:
            await self._transaction.rollback()
            raise


class UpdateCameraHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        camera_repository: CameraRepository,
        camera_free_time_repository: CameraFreeTimeRepository,
        transaction: TransactionManager,
        service: EquipmentService,
    ) -> None:
        self._user_repository = user_repository
        self._camera_repository = camera_repository
        self._camera_free_time_repository = camera_free_time_repository
        self._transaction = transaction
        self._service = service

    async def __call__(self, command: UpdateCameraCommand) -> None:
        user = await self._user_repository.get(command.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")

        camera = await self._camera_repository.get(command.camera_id)
        if camera is None:
            raise EntityNotFoundError("Camera")

        windows = await self._camera_free_time_repository.list_by_obj_id(camera.oid)

        try:
            self._service.update(user, camera, windows)
            camera.title = command.title
            camera.description = command.description
            camera.type = command.type
            await self._camera_repository.update(camera)
            await self._transaction.commit()
        except Exception:
            await self._transaction.rollback()
            raise


class UpdateCameraTripodHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        camera_tripod_repository: CameraTripodRepository,
        camera_tripod_free_time_repository: CameraTripodFreeTimeRepository,
        transaction: TransactionManager,
        service: EquipmentService,
    ) -> None:
        self._user_repository = user_repository
        self._camera_tripod_repository = camera_tripod_repository
        self._camera_tripod_free_time_repository = camera_tripod_free_time_repository
        self._transaction = transaction
        self._service = service

    async def __call__(self, command: UpdateCameraTripodCommand) -> None:
        user = await self._user_repository.get(command.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")

        camera_tripod = await self._camera_tripod_repository.get(
            command.camera_tripod_id
        )
        if camera_tripod is None:
            raise EntityNotFoundError("CameraTripod")

        windows = await self._camera_tripod_free_time_repository.list_by_obj_id(
            camera_tripod.oid
        )

        try:
            self._service.update(user, camera_tripod, windows)
            camera_tripod.title = command.title
            camera_tripod.description = command.description
            camera_tripod.type = command.type
            await self._camera_tripod_repository.update(camera_tripod)
            await self._transaction.commit()
        except Exception:
            await self._transaction.rollback()
            raise


class UpdateLightHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        light_repository: LightRepository,
        light_free_time_repository: LightFreeTimeRepository,
        transaction: TransactionManager,
        service: EquipmentService,
    ) -> None:
        self._user_repository = user_repository
        self._light_repository = light_repository
        self._light_free_time_repository = light_free_time_repository
        self._transaction = transaction
        self._service = service

    async def __call__(self, command: UpdateLightCommand) -> None:
        user = await self._user_repository.get(command.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")

        light = await self._light_repository.get(command.light_id)
        if light is None:
            raise EntityNotFoundError("Light")

        windows = await self._light_free_time_repository.list_by_obj_id(light.oid)

        try:
            self._service.update(user, light, windows)
            light.title = command.title
            light.description = command.description
            light.type = command.type
            await self._light_repository.update(light)
            await self._transaction.commit()
        except Exception:
            await self._transaction.rollback()
            raise


class UpdateLightTripodHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        light_tripod_repository: LightTripodRepository,
        light_tripod_free_time_repository: LightTripodFreeTimeRepository,
        transaction: TransactionManager,
        service: EquipmentService,
    ) -> None:
        self._user_repository = user_repository
        self._light_tripod_repository = light_tripod_repository
        self._light_tripod_free_time_repository = light_tripod_free_time_repository
        self._transaction = transaction
        self._service = service

    async def __call__(self, command: UpdateLightTripodCommand) -> None:
        user = await self._user_repository.get(command.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")

        light_tripod = await self._light_tripod_repository.get(command.light_tripod_id)
        if light_tripod is None:
            raise EntityNotFoundError("LightTripod")

        windows = await self._light_tripod_free_time_repository.list_by_obj_id(
            light_tripod.oid
        )

        try:
            self._service.update(user, light_tripod, windows)
            light_tripod.title = command.title
            light_tripod.description = command.description
            light_tripod.type = command.type
            await self._light_tripod_repository.update(light_tripod)
            await self._transaction.commit()
        except Exception:
            await self._transaction.rollback()
            raise


class UpdateSoundHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        sound_repository: SoundRepository,
        sound_free_time_repository: SoundFreeTimeRepository,
        transaction: TransactionManager,
        service: EquipmentService,
    ) -> None:
        self._user_repository = user_repository
        self._sound_repository = sound_repository
        self._sound_free_time_repository = sound_free_time_repository
        self._transaction = transaction
        self._service = service

    async def __call__(self, command: UpdateSoundCommand) -> None:
        user = await self._user_repository.get(command.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")

        sound = await self._sound_repository.get(command.sound_id)
        if sound is None:
            raise EntityNotFoundError("Sound")

        windows = await self._sound_free_time_repository.list_by_obj_id(sound.oid)

        try:
            self._service.update(user, sound, windows)
            sound.title = command.title
            sound.description = command.description
            sound.type = command.type
            await self._sound_repository.update(sound)
            await self._transaction.commit()
        except Exception:
            await self._transaction.rollback()
            raise


class UpdateRequisiteHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        requisite_repository: RequisiteRepository,
        requisite_free_time_repository: RequisiteFreeTimeRepository,
        transaction: TransactionManager,
        service: EquipmentService,
    ) -> None:
        self._user_repository = user_repository
        self._requisite_repository = requisite_repository
        self._requisite_free_time_repository = requisite_free_time_repository
        self._transaction = transaction
        self._service = service

    async def __call__(self, command: UpdateRequisiteCommand) -> None:
        user = await self._user_repository.get(command.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")

        requisite = await self._requisite_repository.get(command.requisite_id)
        if requisite is None:
            raise EntityNotFoundError("Requisite")

        windows = await self._requisite_free_time_repository.list_by_obj_id(
            requisite.oid
        )

        try:
            self._service.update(user, requisite, windows)
            requisite.title = command.title
            requisite.description = command.description
            requisite.type = command.type
            requisite.size = command.size
            await self._requisite_repository.update(requisite)
            await self._transaction.commit()
        except Exception:
            await self._transaction.rollback()
            raise
