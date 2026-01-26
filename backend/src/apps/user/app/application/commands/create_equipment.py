from dataclasses import dataclass
from datetime import datetime

from app.application.errors.errors import UserNotFoundError
from app.application.ports.repositories import (
    CameraRepository,
    CameraTripodRepository,
    LightRepository,
    LightTripodRepository,
    RequisiteRepository,
    SoundRepository,
    UserRepository,
)
from app.application.ports.transaction import TransactionManager
from app.domain.entity.base import (
    BaseId,
    Camera,
    CameraTripod,
    Light,
    LightTripod,
    Requisite,
    Sound,
)
from app.domain.service.equipment_service import EquipmentService
from app.infrastructure.generation import AbstractGenerationID


@dataclass(frozen=True, slots=True, kw_only=True)
class CreateCameraCommand:
    user_id: BaseId
    title: str
    description: str
    type: str


@dataclass(frozen=True, slots=True, kw_only=True)
class CreateCameraTripodCommand:
    user_id: BaseId
    title: str
    description: str
    type: str


@dataclass(frozen=True, slots=True, kw_only=True)
class CreateLightCommand:
    user_id: BaseId
    title: str
    description: str
    type: str


@dataclass(frozen=True, slots=True, kw_only=True)
class CreateLightTripodCommand:
    user_id: BaseId
    title: str
    description: str
    type: str


@dataclass(frozen=True, slots=True, kw_only=True)
class CreateSoundCommand:
    user_id: BaseId
    title: str
    description: str
    type: str


@dataclass(frozen=True, slots=True, kw_only=True)
class CreateRequisiteCommand:
    user_id: BaseId
    title: str
    description: str
    type: str
    size: str


class CreateCameraHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        camera_repository: CameraRepository,
        transaction: TransactionManager,
        id_generator: AbstractGenerationID,
        service: EquipmentService,
    ) -> None:
        self._user_repository = user_repository
        self._camera_repository = camera_repository
        self._transaction = transaction
        self._id_generator = id_generator
        self._service = service

    async def __call__(self, command: CreateCameraCommand) -> None:
        user = await self._user_repository.get(command.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")

        equipment = Camera(
            oid=self._id_generator(),
            users_id=user.oid,
            title=command.title,
            description=command.description,
            type=command.type,
            create_at=datetime.now(),
        )

        try:
            self._service.create(user, equipment)
            await self._camera_repository.add(equipment)
            await self._transaction.commit()
        except Exception:
            await self._transaction.rollback()
            raise


class CreateCameraTripodHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        camera_tripod_repository: CameraTripodRepository,
        transaction: TransactionManager,
        id_generator: AbstractGenerationID,
        service: EquipmentService,
    ) -> None:
        self._user_repository = user_repository
        self._camera_tripod_repository = camera_tripod_repository
        self._transaction = transaction
        self._id_generator = id_generator
        self._service = service

    async def __call__(self, command: CreateCameraTripodCommand) -> None:
        user = await self._user_repository.get(command.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")

        equipment = CameraTripod(
            oid=self._id_generator(),
            users_id=user.oid,
            title=command.title,
            description=command.description,
            type=command.type,
            create_at=datetime.now(),
        )

        try:
            self._service.create(user, equipment)
            await self._camera_tripod_repository.add(equipment)
            await self._transaction.commit()
        except Exception:
            await self._transaction.rollback()
            raise


class CreateLightHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        light_repository: LightRepository,
        transaction: TransactionManager,
        id_generator: AbstractGenerationID,
        service: EquipmentService,
    ) -> None:
        self._user_repository = user_repository
        self._light_repository = light_repository
        self._transaction = transaction
        self._id_generator = id_generator
        self._service = service

    async def __call__(self, command: CreateLightCommand) -> None:
        user = await self._user_repository.get(command.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")

        equipment = Light(
            oid=self._id_generator(),
            users_id=user.oid,
            title=command.title,
            description=command.description,
            type=command.type,
            create_at=datetime.now(),
        )

        try:
            self._service.create(user, equipment)
            await self._light_repository.add(equipment)
            await self._transaction.commit()
        except Exception:
            await self._transaction.rollback()
            raise


class CreateLightTripodHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        light_tripod_repository: LightTripodRepository,
        transaction: TransactionManager,
        id_generator: AbstractGenerationID,
        service: EquipmentService,
    ) -> None:
        self._user_repository = user_repository
        self._light_tripod_repository = light_tripod_repository
        self._transaction = transaction
        self._id_generator = id_generator
        self._service = service

    async def __call__(self, command: CreateLightTripodCommand) -> None:
        user = await self._user_repository.get(command.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")

        equipment = LightTripod(
            oid=self._id_generator(),
            users_id=user.oid,
            title=command.title,
            description=command.description,
            type=command.type,
            create_at=datetime.now(),
        )

        try:
            self._service.create(user, equipment)
            await self._light_tripod_repository.add(equipment)
            await self._transaction.commit()
        except Exception:
            await self._transaction.rollback()
            raise


class CreateSoundHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        sound_repository: SoundRepository,
        transaction: TransactionManager,
        id_generator: AbstractGenerationID,
        service: EquipmentService,
    ) -> None:
        self._user_repository = user_repository
        self._sound_repository = sound_repository
        self._transaction = transaction
        self._id_generator = id_generator
        self._service = service

    async def __call__(self, command: CreateSoundCommand) -> None:
        user = await self._user_repository.get(command.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")

        equipment = Sound(
            oid=self._id_generator(),
            users_id=user.oid,
            title=command.title,
            description=command.description,
            type=command.type,
            create_at=datetime.now(),
        )

        try:
            self._service.create(user, equipment)
            await self._sound_repository.add(equipment)
            await self._transaction.commit()
        except Exception:
            await self._transaction.rollback()
            raise


class CreateRequisiteHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        requisite_repository: RequisiteRepository,
        transaction: TransactionManager,
        id_generator: AbstractGenerationID,
        service: EquipmentService,
    ) -> None:
        self._user_repository = user_repository
        self._requisite_repository = requisite_repository
        self._transaction = transaction
        self._id_generator = id_generator
        self._service = service

    async def __call__(self, command: CreateRequisiteCommand) -> None:
        user = await self._user_repository.get(command.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")

        equipment = Requisite(
            oid=self._id_generator(),
            users_id=user.oid,
            title=command.title,
            description=command.description,
            type=command.type,
            size=command.size,
            create_at=datetime.now(),
        )

        try:
            self._service.create(user, equipment)
            await self._requisite_repository.add(equipment)
            await self._transaction.commit()
        except Exception:
            await self._transaction.rollback()
            raise
