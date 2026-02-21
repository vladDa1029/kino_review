from typing import Callable, Iterable

from dishka import Provider, Scope
from faststream.rabbit import RabbitBroker
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
from structlog.stdlib import BoundLogger

from app.application.commands.add_image import AddImageHandler
from app.application.commands.add_equipment_free_time import (
    AddCameraFreeTimeHandler,
    AddCameraTripodFreeTimeHandler,
    AddLightFreeTimeHandler,
    AddLightTripodFreeTimeHandler,
    AddMicrofonFreeTimeHandler,
    AddRequisiteFreeTimeHandler,
    AddSoundFreeTimeHandler,
)
from app.application.commands.add_spare_time import AddSpareTimeHandler
from app.application.commands.create_description import CreateDescriptionHandler
from app.application.commands.create_equipment import (
    CreateCameraHandler,
    CreateCameraTripodHandler,
    CreateLightHandler,
    CreateLightTripodHandler,
    CreateRequisiteHandler,
    CreateSoundHandler,
)
from app.application.commands.create_microfon import CreateMicrofonHandler
from app.application.commands.delete_equipment import (
    DeleteCameraHandler,
    DeleteCameraTripodHandler,
    DeleteLightHandler,
    DeleteLightTripodHandler,
    DeleteMicrofonHandler,
    DeleteRequisiteHandler,
    DeleteSoundHandler,
)
from app.application.commands.remove_image import RemoveImageHandler
from app.application.commands.reserve_availability import ReserveAvailabilityHandler
from app.application.commands.user_registered import UserRegisteredHandler
from app.application.commands.update_description import UpdateDescriptionHandler
from app.application.commands.update_equipment import (
    UpdateCameraHandler,
    UpdateCameraTripodHandler,
    UpdateLightHandler,
    UpdateLightTripodHandler,
    UpdateMicrofonHandler,
    UpdateRequisiteHandler,
    UpdateSoundHandler,
)
from app.application.queries.list_equipment import (
    ListCamerasHandler,
    ListCameraTripodsHandler,
    ListLightsHandler,
    ListLightTripodsHandler,
    ListMicrofonsHandler,
    ListRequisitesHandler,
    ListSoundsHandler,
)
from app.application.queries.images import (
    GetRequisiteImageHandler,
    ListRequisiteImagesHandler,
)
from app.application.ports.repositories import (
    CameraFreeTimeRepository,
    CameraRepository,
    CameraTripodRepository,
    CameraTripodFreeTimeRepository,
    DescriptionRepository,
    ImageRepository,
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
from app.application.ports.storage import FileStorage
from app.application.ports.transaction import TransactionManager
from app.config import (
    DatabaseSettings,
    ImageSettings,
    Log,
    Rabbitmq,
    SQLAlchemySettings,
    StorageSettings,
)
from app.domain.policy.active_user import ActiveUserPolicy
from app.domain.policy.description import DescriptionOwnershipPolicy
from app.domain.policy.image_ownership import ImageOwnershipPolicy
from app.domain.policy.ownership import OwnershipPolicy
from app.domain.policy.resource_lock import ResourceUnlockedPolicy
from app.domain.policy.single_description import SingleDescriptionPolicy
from app.domain.service.availability_service import AvailabilityService
from app.domain.service.description_service import DescriptionService
from app.domain.service.equipment_free_time_service import EquipmentFreeTimeService
from app.domain.service.equipment_service import EquipmentService
from app.domain.service.free_time_service import FreeTimeService
from app.domain.service.image_service import ImageService
from app.domain.specification.description_identity import DescriptionIdentitySpec
from app.domain.specification.time_overlap import NonOverlappingTimeSpec
from app.domain.specification.time_within import TimeWithinWindowSpec
from app.domain.entity.base import BaseId
from app.infrastructure.adapters.repository import (
    CameraFreeTimeSqlAlchemyRepository,
    CameraSqlAlchemyRepository,
    CameraTripodSqlAlchemyRepository,
    CameraTripodFreeTimeSqlAlchemyRepository,
    DescriptionSqlAlchemyRepository,
    ImageSqlAlchemyRepository,
    LightFreeTimeSqlAlchemyRepository,
    LightSqlAlchemyRepository,
    LightTripodFreeTimeSqlAlchemyRepository,
    LightTripodSqlAlchemyRepository,
    MicrofonFreeTimeSqlAlchemyRepository,
    MicrofonSqlAlchemyRepository,
    RequisiteFreeTimeSqlAlchemyRepository,
    RequisiteSqlAlchemyRepository,
    SoundFreeTimeSqlAlchemyRepository,
    SoundSqlAlchemyRepository,
    SpareTimeSqlAlchemyRepository,
    UserSqlAlchemyRepository,
)
from app.infrastructure.adapters.storage import create_file_storage
from app.infrastructure.database import get_engine, get_session, get_sessionmaker
from app.infrastructure.generation import AbstractGenerationID, GenerationUUID
from app.infrastructure.transactions import TransactionManagerAlchemy


def settings_provider() -> Provider:
    provider = Provider(scope=Scope.APP)
    provider.from_context(provides=Log)
    provider.from_context(provides=DatabaseSettings)
    provider.from_context(provides=SQLAlchemySettings)
    provider.from_context(provides=Rabbitmq)
    provider.from_context(provides=StorageSettings)
    provider.from_context(provides=ImageSettings)
    return provider


def broker_provider() -> Provider:
    provider = Provider(scope=Scope.APP)
    provider.from_context(provides=RabbitBroker)
    return provider


def get_logger(settings: Log) -> BoundLogger:
    return structlog.get_logger(settings.logger_name)


def logger_provider() -> Provider:
    provider = Provider(scope=Scope.APP)
    provider.provide(get_logger, provides=BoundLogger)
    return provider


def id_factory_provider(
    id_generator: AbstractGenerationID,
) -> Callable[[], BaseId]:
    return id_generator


def db_provider() -> Provider:
    provider = Provider(scope=Scope.REQUEST)
    provider.provide(get_engine, scope=Scope.APP)
    provider.provide(get_sessionmaker, scope=Scope.APP)
    provider.provide(get_session, provides=AsyncSession)
    return provider


def services_provider() -> Provider:
    provider = Provider(scope=Scope.REQUEST)
    provider.provide(source=TransactionManagerAlchemy, provides=TransactionManager)
    provider.provide(source=GenerationUUID, provides=AbstractGenerationID)
    provider.provide(id_factory_provider, provides=Callable[[], BaseId])
    provider.provide(source=ActiveUserPolicy)
    provider.provide(source=OwnershipPolicy)
    provider.provide(source=ResourceUnlockedPolicy)
    provider.provide(source=DescriptionOwnershipPolicy)
    provider.provide(source=SingleDescriptionPolicy)
    provider.provide(source=ImageOwnershipPolicy)
    provider.provide(source=NonOverlappingTimeSpec)
    provider.provide(source=TimeWithinWindowSpec)
    provider.provide(source=DescriptionIdentitySpec)
    provider.provide(source=AvailabilityService)
    provider.provide(source=DescriptionService)
    provider.provide(source=EquipmentFreeTimeService)
    provider.provide(source=EquipmentService)
    provider.provide(source=FreeTimeService)
    provider.provide(source=ImageService)
    return provider


def storage_provider() -> Provider:
    provider = Provider(scope=Scope.REQUEST)
    provider.provide(create_file_storage, provides=FileStorage)
    return provider


def repository_provider() -> Provider:
    provider = Provider(scope=Scope.REQUEST)
    provider.provide(source=UserSqlAlchemyRepository, provides=UserRepository)
    provider.provide(
        source=DescriptionSqlAlchemyRepository, provides=DescriptionRepository
    )
    provider.provide(source=SpareTimeSqlAlchemyRepository, provides=SpareTimeRepository)
    provider.provide(
        source=MicrofonFreeTimeSqlAlchemyRepository,
        provides=MicrofonFreeTimeRepository,
    )
    provider.provide(
        source=CameraFreeTimeSqlAlchemyRepository,
        provides=CameraFreeTimeRepository,
    )
    provider.provide(
        source=CameraTripodFreeTimeSqlAlchemyRepository,
        provides=CameraTripodFreeTimeRepository,
    )
    provider.provide(
        source=LightFreeTimeSqlAlchemyRepository,
        provides=LightFreeTimeRepository,
    )
    provider.provide(
        source=LightTripodFreeTimeSqlAlchemyRepository,
        provides=LightTripodFreeTimeRepository,
    )
    provider.provide(
        source=SoundFreeTimeSqlAlchemyRepository,
        provides=SoundFreeTimeRepository,
    )
    provider.provide(
        source=RequisiteFreeTimeSqlAlchemyRepository,
        provides=RequisiteFreeTimeRepository,
    )
    provider.provide(source=MicrofonSqlAlchemyRepository, provides=MicrofonRepository)
    provider.provide(source=CameraSqlAlchemyRepository, provides=CameraRepository)
    provider.provide(
        source=CameraTripodSqlAlchemyRepository,
        provides=CameraTripodRepository,
    )
    provider.provide(source=LightSqlAlchemyRepository, provides=LightRepository)
    provider.provide(
        source=LightTripodSqlAlchemyRepository,
        provides=LightTripodRepository,
    )
    provider.provide(source=SoundSqlAlchemyRepository, provides=SoundRepository)
    provider.provide(source=RequisiteSqlAlchemyRepository, provides=RequisiteRepository)
    provider.provide(source=ImageSqlAlchemyRepository, provides=ImageRepository)
    return provider


def use_case_provider() -> Provider:
    provider = Provider(scope=Scope.REQUEST)
    provider.provide(source=AddImageHandler)
    provider.provide(source=AddMicrofonFreeTimeHandler)
    provider.provide(source=AddCameraFreeTimeHandler)
    provider.provide(source=AddCameraTripodFreeTimeHandler)
    provider.provide(source=AddLightFreeTimeHandler)
    provider.provide(source=AddLightTripodFreeTimeHandler)
    provider.provide(source=AddSoundFreeTimeHandler)
    provider.provide(source=AddRequisiteFreeTimeHandler)
    provider.provide(source=AddSpareTimeHandler)
    provider.provide(source=CreateCameraHandler)
    provider.provide(source=CreateCameraTripodHandler)
    provider.provide(source=CreateDescriptionHandler)
    provider.provide(source=CreateLightHandler)
    provider.provide(source=CreateLightTripodHandler)
    provider.provide(source=CreateMicrofonHandler)
    provider.provide(source=CreateRequisiteHandler)
    provider.provide(source=CreateSoundHandler)
    provider.provide(source=DeleteCameraHandler)
    provider.provide(source=DeleteCameraTripodHandler)
    provider.provide(source=DeleteLightHandler)
    provider.provide(source=DeleteLightTripodHandler)
    provider.provide(source=DeleteMicrofonHandler)
    provider.provide(source=DeleteRequisiteHandler)
    provider.provide(source=DeleteSoundHandler)
    provider.provide(source=RemoveImageHandler)
    provider.provide(source=ReserveAvailabilityHandler)
    provider.provide(source=UserRegisteredHandler)
    provider.provide(source=ListMicrofonsHandler)
    provider.provide(source=ListCamerasHandler)
    provider.provide(source=ListCameraTripodsHandler)
    provider.provide(source=ListLightsHandler)
    provider.provide(source=ListLightTripodsHandler)
    provider.provide(source=ListSoundsHandler)
    provider.provide(source=ListRequisitesHandler)
    provider.provide(source=ListRequisiteImagesHandler)
    provider.provide(source=GetRequisiteImageHandler)
    provider.provide(source=UpdateCameraHandler)
    provider.provide(source=UpdateCameraTripodHandler)
    provider.provide(source=UpdateDescriptionHandler)
    provider.provide(source=UpdateLightHandler)
    provider.provide(source=UpdateLightTripodHandler)
    provider.provide(source=UpdateMicrofonHandler)
    provider.provide(source=UpdateRequisiteHandler)
    provider.provide(source=UpdateSoundHandler)
    return provider


def setup_providers() -> Iterable[Provider]:
    return (
        settings_provider(),
        broker_provider(),
        logger_provider(),
        db_provider(),
        services_provider(),
        storage_provider(),
        repository_provider(),
        use_case_provider(),
    )
