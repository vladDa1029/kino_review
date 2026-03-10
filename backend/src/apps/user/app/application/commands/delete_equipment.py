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
class DeleteMicrofonCommand:
    user_id: BaseId
    microfon_id: BaseId


@dataclass(frozen=True, slots=True, kw_only=True)
class DeleteCameraCommand:
    user_id: BaseId
    camera_id: BaseId


@dataclass(frozen=True, slots=True, kw_only=True)
class DeleteCameraTripodCommand:
    user_id: BaseId
    camera_tripod_id: BaseId


@dataclass(frozen=True, slots=True, kw_only=True)
class DeleteLightCommand:
    user_id: BaseId
    light_id: BaseId


@dataclass(frozen=True, slots=True, kw_only=True)
class DeleteLightTripodCommand:
    user_id: BaseId
    light_tripod_id: BaseId


@dataclass(frozen=True, slots=True, kw_only=True)
class DeleteSoundCommand:
    user_id: BaseId
    sound_id: BaseId


@dataclass(frozen=True, slots=True, kw_only=True)
class DeleteRequisiteCommand:
    user_id: BaseId
    requisite_id: BaseId


class DeleteMicrofonHandler:
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

    async def __call__(self, command: DeleteMicrofonCommand) -> None:
        user = await self._user_repository.get(command.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")

        microfon = await self._microfon_repository.get(command.microfon_id)
        if microfon is None:
            raise EntityNotFoundError("Microfon")

        windows = await self._microfon_free_time_repository.list_by_obj_id(microfon.oid)

        try:
            self._service.delete(user, microfon, windows)
            await self._microfon_repository.delete(microfon)
            await self._transaction.commit()
        except Exception:
            await self._transaction.rollback()
            raise


class DeleteCameraHandler:
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

    async def __call__(self, command: DeleteCameraCommand) -> None:
        user = await self._user_repository.get(command.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")

        camera = await self._camera_repository.get(command.camera_id)
        if camera is None:
            raise EntityNotFoundError("Camera")

        windows = await self._camera_free_time_repository.list_by_obj_id(camera.oid)

        try:
            self._service.delete(user, camera, windows)
            await self._camera_repository.delete(camera)
            await self._transaction.commit()
        except Exception:
            await self._transaction.rollback()
            raise


class DeleteCameraTripodHandler:
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

    async def __call__(self, command: DeleteCameraTripodCommand) -> None:
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
            self._service.delete(user, camera_tripod, windows)
            await self._camera_tripod_repository.delete(camera_tripod)
            await self._transaction.commit()
        except Exception:
            await self._transaction.rollback()
            raise


class DeleteLightHandler:
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

    async def __call__(self, command: DeleteLightCommand) -> None:
        user = await self._user_repository.get(command.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")

        light = await self._light_repository.get(command.light_id)
        if light is None:
            raise EntityNotFoundError("Light")

        windows = await self._light_free_time_repository.list_by_obj_id(light.oid)

        try:
            self._service.delete(user, light, windows)
            await self._light_repository.delete(light)
            await self._transaction.commit()
        except Exception:
            await self._transaction.rollback()
            raise


class DeleteLightTripodHandler:
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

    async def __call__(self, command: DeleteLightTripodCommand) -> None:
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
            self._service.delete(user, light_tripod, windows)
            await self._light_tripod_repository.delete(light_tripod)
            await self._transaction.commit()
        except Exception:
            await self._transaction.rollback()
            raise


class DeleteSoundHandler:
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

    async def __call__(self, command: DeleteSoundCommand) -> None:
        user = await self._user_repository.get(command.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")

        sound = await self._sound_repository.get(command.sound_id)
        if sound is None:
            raise EntityNotFoundError("Sound")

        windows = await self._sound_free_time_repository.list_by_obj_id(sound.oid)

        try:
            self._service.delete(user, sound, windows)
            await self._sound_repository.delete(sound)
            await self._transaction.commit()
        except Exception:
            await self._transaction.rollback()
            raise


class DeleteRequisiteHandler:
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

    async def __call__(self, command: DeleteRequisiteCommand) -> None:
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
            self._service.delete(user, requisite, windows)
            await self._requisite_repository.delete(requisite)
            await self._transaction.commit()
        except Exception:
            await self._transaction.rollback()
            raise
