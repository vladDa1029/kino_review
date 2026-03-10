from dataclasses import dataclass
from datetime import datetime

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
from app.application.ports.transaction import TransactionManager
from app.domain.entity.base import BaseId, Spare_time
from app.domain.service.equipment_free_time_service import EquipmentFreeTimeService
from app.infrastructure.generation import AbstractGenerationID


@dataclass(frozen=True, slots=True, kw_only=True)
class AddMicrofonFreeTimeCommand:
    user_id: BaseId
    microfon_id: BaseId
    start_time: datetime
    end_time: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class AddCameraFreeTimeCommand:
    user_id: BaseId
    camera_id: BaseId
    start_time: datetime
    end_time: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class AddCameraTripodFreeTimeCommand:
    user_id: BaseId
    camera_tripod_id: BaseId
    start_time: datetime
    end_time: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class AddLightFreeTimeCommand:
    user_id: BaseId
    light_id: BaseId
    start_time: datetime
    end_time: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class AddLightTripodFreeTimeCommand:
    user_id: BaseId
    light_tripod_id: BaseId
    start_time: datetime
    end_time: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class AddSoundFreeTimeCommand:
    user_id: BaseId
    sound_id: BaseId
    start_time: datetime
    end_time: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class AddRequisiteFreeTimeCommand:
    user_id: BaseId
    requisite_id: BaseId
    start_time: datetime
    end_time: datetime


class AddMicrofonFreeTimeHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        microfon_repository: MicrofonRepository,
        microfon_free_time_repository: MicrofonFreeTimeRepository,
        transaction: TransactionManager,
        id_generator: AbstractGenerationID,
        service: EquipmentFreeTimeService,
    ) -> None:
        self._user_repository = user_repository
        self._microfon_repository = microfon_repository
        self._microfon_free_time_repository = microfon_free_time_repository
        self._transaction = transaction
        self._id_generator = id_generator
        self._service = service

    async def __call__(self, command: AddMicrofonFreeTimeCommand) -> None:
        user = await self._user_repository.get(command.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")

        microfon = await self._microfon_repository.get(command.microfon_id)
        if microfon is None:
            raise EntityNotFoundError("Microfon")

        timings = await self._microfon_free_time_repository.list_by_obj_id(microfon.oid)
        new_timing = Spare_time(
            oid=self._id_generator(),
            obj=microfon.oid,
            start_time=command.start_time,
            end_time=command.end_time,
        )

        try:
            self._service.add_timing(user, microfon, timings, new_timing)
            await self._microfon_free_time_repository.add(new_timing)
            await self._transaction.commit()
        except Exception:
            await self._transaction.rollback()
            raise


class AddCameraFreeTimeHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        camera_repository: CameraRepository,
        camera_free_time_repository: CameraFreeTimeRepository,
        transaction: TransactionManager,
        id_generator: AbstractGenerationID,
        service: EquipmentFreeTimeService,
    ) -> None:
        self._user_repository = user_repository
        self._camera_repository = camera_repository
        self._camera_free_time_repository = camera_free_time_repository
        self._transaction = transaction
        self._id_generator = id_generator
        self._service = service

    async def __call__(self, command: AddCameraFreeTimeCommand) -> None:
        user = await self._user_repository.get(command.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")

        camera = await self._camera_repository.get(command.camera_id)
        if camera is None:
            raise EntityNotFoundError("Camera")

        timings = await self._camera_free_time_repository.list_by_obj_id(camera.oid)
        new_timing = Spare_time(
            oid=self._id_generator(),
            obj=camera.oid,
            start_time=command.start_time,
            end_time=command.end_time,
        )

        try:
            self._service.add_timing(user, camera, timings, new_timing)
            await self._camera_free_time_repository.add(new_timing)
            await self._transaction.commit()
        except Exception:
            await self._transaction.rollback()
            raise


class AddCameraTripodFreeTimeHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        camera_tripod_repository: CameraTripodRepository,
        camera_tripod_free_time_repository: CameraTripodFreeTimeRepository,
        transaction: TransactionManager,
        id_generator: AbstractGenerationID,
        service: EquipmentFreeTimeService,
    ) -> None:
        self._user_repository = user_repository
        self._camera_tripod_repository = camera_tripod_repository
        self._camera_tripod_free_time_repository = camera_tripod_free_time_repository
        self._transaction = transaction
        self._id_generator = id_generator
        self._service = service

    async def __call__(self, command: AddCameraTripodFreeTimeCommand) -> None:
        user = await self._user_repository.get(command.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")

        camera_tripod = await self._camera_tripod_repository.get(
            command.camera_tripod_id
        )
        if camera_tripod is None:
            raise EntityNotFoundError("CameraTripod")

        timings = await self._camera_tripod_free_time_repository.list_by_obj_id(
            camera_tripod.oid
        )
        new_timing = Spare_time(
            oid=self._id_generator(),
            obj=camera_tripod.oid,
            start_time=command.start_time,
            end_time=command.end_time,
        )

        try:
            self._service.add_timing(user, camera_tripod, timings, new_timing)
            await self._camera_tripod_free_time_repository.add(new_timing)
            await self._transaction.commit()
        except Exception:
            await self._transaction.rollback()
            raise


class AddLightFreeTimeHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        light_repository: LightRepository,
        light_free_time_repository: LightFreeTimeRepository,
        transaction: TransactionManager,
        id_generator: AbstractGenerationID,
        service: EquipmentFreeTimeService,
    ) -> None:
        self._user_repository = user_repository
        self._light_repository = light_repository
        self._light_free_time_repository = light_free_time_repository
        self._transaction = transaction
        self._id_generator = id_generator
        self._service = service

    async def __call__(self, command: AddLightFreeTimeCommand) -> None:
        user = await self._user_repository.get(command.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")

        light = await self._light_repository.get(command.light_id)
        if light is None:
            raise EntityNotFoundError("Light")

        timings = await self._light_free_time_repository.list_by_obj_id(light.oid)
        new_timing = Spare_time(
            oid=self._id_generator(),
            obj=light.oid,
            start_time=command.start_time,
            end_time=command.end_time,
        )

        try:
            self._service.add_timing(user, light, timings, new_timing)
            await self._light_free_time_repository.add(new_timing)
            await self._transaction.commit()
        except Exception:
            await self._transaction.rollback()
            raise


class AddLightTripodFreeTimeHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        light_tripod_repository: LightTripodRepository,
        light_tripod_free_time_repository: LightTripodFreeTimeRepository,
        transaction: TransactionManager,
        id_generator: AbstractGenerationID,
        service: EquipmentFreeTimeService,
    ) -> None:
        self._user_repository = user_repository
        self._light_tripod_repository = light_tripod_repository
        self._light_tripod_free_time_repository = light_tripod_free_time_repository
        self._transaction = transaction
        self._id_generator = id_generator
        self._service = service

    async def __call__(self, command: AddLightTripodFreeTimeCommand) -> None:
        user = await self._user_repository.get(command.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")

        light_tripod = await self._light_tripod_repository.get(command.light_tripod_id)
        if light_tripod is None:
            raise EntityNotFoundError("LightTripod")

        timings = await self._light_tripod_free_time_repository.list_by_obj_id(
            light_tripod.oid
        )
        new_timing = Spare_time(
            oid=self._id_generator(),
            obj=light_tripod.oid,
            start_time=command.start_time,
            end_time=command.end_time,
        )

        try:
            self._service.add_timing(user, light_tripod, timings, new_timing)
            await self._light_tripod_free_time_repository.add(new_timing)
            await self._transaction.commit()
        except Exception:
            await self._transaction.rollback()
            raise


class AddSoundFreeTimeHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        sound_repository: SoundRepository,
        sound_free_time_repository: SoundFreeTimeRepository,
        transaction: TransactionManager,
        id_generator: AbstractGenerationID,
        service: EquipmentFreeTimeService,
    ) -> None:
        self._user_repository = user_repository
        self._sound_repository = sound_repository
        self._sound_free_time_repository = sound_free_time_repository
        self._transaction = transaction
        self._id_generator = id_generator
        self._service = service

    async def __call__(self, command: AddSoundFreeTimeCommand) -> None:
        user = await self._user_repository.get(command.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")

        sound = await self._sound_repository.get(command.sound_id)
        if sound is None:
            raise EntityNotFoundError("Sound")

        timings = await self._sound_free_time_repository.list_by_obj_id(sound.oid)
        new_timing = Spare_time(
            oid=self._id_generator(),
            obj=sound.oid,
            start_time=command.start_time,
            end_time=command.end_time,
        )

        try:
            self._service.add_timing(user, sound, timings, new_timing)
            await self._sound_free_time_repository.add(new_timing)
            await self._transaction.commit()
        except Exception:
            await self._transaction.rollback()
            raise


class AddRequisiteFreeTimeHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        requisite_repository: RequisiteRepository,
        requisite_free_time_repository: RequisiteFreeTimeRepository,
        transaction: TransactionManager,
        id_generator: AbstractGenerationID,
        service: EquipmentFreeTimeService,
    ) -> None:
        self._user_repository = user_repository
        self._requisite_repository = requisite_repository
        self._requisite_free_time_repository = requisite_free_time_repository
        self._transaction = transaction
        self._id_generator = id_generator
        self._service = service

    async def __call__(self, command: AddRequisiteFreeTimeCommand) -> None:
        user = await self._user_repository.get(command.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")

        requisite = await self._requisite_repository.get(command.requisite_id)
        if requisite is None:
            raise EntityNotFoundError("Requisite")

        timings = await self._requisite_free_time_repository.list_by_obj_id(
            requisite.oid
        )
        new_timing = Spare_time(
            oid=self._id_generator(),
            obj=requisite.oid,
            start_time=command.start_time,
            end_time=command.end_time,
        )

        try:
            self._service.add_timing(user, requisite, timings, new_timing)
            await self._requisite_free_time_repository.add(new_timing)
            await self._transaction.commit()
        except Exception:
            await self._transaction.rollback()
            raise
