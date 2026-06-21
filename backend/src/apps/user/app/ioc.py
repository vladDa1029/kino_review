from typing import Callable, Iterable

import structlog
from dishka import Provider, Scope
from faststream.rabbit import RabbitBroker
from sqlalchemy.ext.asyncio import AsyncSession
from structlog.stdlib import BoundLogger

from app.application.commands.add_equipment_free_time import (
    AddCameraFreeTimeHandler,
    AddCameraTripodFreeTimeHandler,
    AddLightFreeTimeHandler,
    AddLightTripodFreeTimeHandler,
    AddMicrofonFreeTimeHandler,
    AddRequisiteFreeTimeHandler,
    AddSoundFreeTimeHandler,
)
from app.application.commands.add_image import AddImageHandler
from app.application.commands.add_spare_time import AddSpareTimeHandler
from app.application.commands.approval_notifications import (
    HandleParticipantApprovalRequestedHandler,
    HandleProjectMemberInvitationRequestedHandler,
    HandleResourceApprovalRequestedHandler,
    HandleShiftReminderRequestedHandler,
)
from app.application.commands.check_availability import CheckAvailabilityHandler
from app.application.commands.confirm_project_invitation import (
    ConfirmProjectInvitationByTokenHandler,
)
from app.application.commands.confirm_reservation import ConfirmReservationByTokenHandler
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
from app.application.commands.delete_spare_time import DeleteSpareTimeHandler
from app.application.commands.remove_image import RemoveImageHandler
from app.application.commands.reserve_availability import ReserveAvailabilityHandler
from app.application.commands.reserve_participant_availability import (
    ReserveParticipantAvailabilityHandler,
)
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
from app.application.commands.update_spare_time import UpdateSpareTimeHandler
from app.application.commands.user_registered import UserRegisteredHandler
from app.application.ports.approvals import ConfirmationTokenPort, ProjectApprovalStatePort
from app.application.ports.broker import EventPublisher
from app.application.ports.repositories import (
    AvailabilityReservationRepository,
    CameraFreeTimeRepository,
    CameraRepository,
    CameraTripodFreeTimeRepository,
    CameraTripodRepository,
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
from app.application.queries.description import GetDescriptionHandler
from app.application.queries.equipment_free_times import (
    ListCameraFreeTimesHandler,
    ListCameraTripodFreeTimesHandler,
    ListLightFreeTimesHandler,
    ListLightTripodFreeTimesHandler,
    ListMicrofonFreeTimesHandler,
    ListRequisiteFreeTimesHandler,
    ListSoundFreeTimesHandler,
)
from app.application.queries.images import (
    GetRequisiteImageHandler,
    ListRequisiteImagesHandler,
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
from app.application.queries.report_snapshot import ProvideShiftReportSnapshotHandler
from app.application.queries.spare_times import (
    GetUserSpareTimeHandler,
    ListUserSpareTimesHandler,
)
from app.application.queries.users import GetUserByEmailHandler, GetUserExistsHandler
from app.application.resource_ownership import ResourceOwnershipResolver
from app.config import (
    ConfirmationSettings,
    DatabaseSettings,
    ImageSettings,
    Log,
    ProjectService,
    Rabbitmq,
    SQLAlchemySettings,
    StorageSettings,
)
from app.domain.entity.base import BaseId
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
from app.infrastructure.adapters.broker import RabbitPublisher
from app.infrastructure.adapters.repository import (
    AvailabilityReservationSqlAlchemyRepository,
    CameraFreeTimeSqlAlchemyRepository,
    CameraSqlAlchemyRepository,
    CameraTripodFreeTimeSqlAlchemyRepository,
    CameraTripodSqlAlchemyRepository,
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
from app.infrastructure.adapters.request_reply import BrokerReplyInbox
from app.infrastructure.adapters.storage import create_file_storage
from app.infrastructure.database import get_engine, get_session, get_sessionmaker
from app.infrastructure.generation import AbstractGenerationID, GenerationUUID
from app.infrastructure.security.confirmation_token import JWTConfirmationTokenService
from app.infrastructure.transactions import TransactionManagerAlchemy
from app.presentation.http.project_service import ProjectApprovalStateBrokerClient


def settings_provider() -> Provider:
    provider = Provider(scope=Scope.APP)
    provider.from_context(provides=Log)
    provider.from_context(provides=DatabaseSettings)
    provider.from_context(provides=SQLAlchemySettings)
    provider.from_context(provides=Rabbitmq)
    provider.from_context(provides=StorageSettings)
    provider.from_context(provides=ImageSettings)
    provider.from_context(provides=ProjectService)
    provider.from_context(provides=ConfirmationSettings)
    provider.from_context(provides=BrokerReplyInbox)
    return provider


def broker_provider() -> Provider:
    provider = Provider(scope=Scope.APP)
    provider.from_context(provides=RabbitBroker)
    provider.provide(source=RabbitPublisher, provides=EventPublisher, scope=Scope.APP)
    provider.provide(
        source=ProjectApprovalStateBrokerClient,
        provides=ProjectApprovalStatePort,
        scope=Scope.APP,
    )
    provider.provide(
        source=JWTConfirmationTokenService,
        provides=ConfirmationTokenPort,
        scope=Scope.APP,
    )
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
    provider.provide(source=ResourceOwnershipResolver)
    return provider


def storage_provider() -> Provider:
    provider = Provider(scope=Scope.REQUEST)
    provider.provide(create_file_storage, provides=FileStorage)
    return provider


def repository_provider() -> Provider:
    provider = Provider(scope=Scope.REQUEST)
    provider.provide(source=UserSqlAlchemyRepository, provides=UserRepository)
    provider.provide(
        source=AvailabilityReservationSqlAlchemyRepository,
        provides=AvailabilityReservationRepository,
    )
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
    provider.provide(source=DeleteSpareTimeHandler)
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
    provider.provide(source=CheckAvailabilityHandler)
    provider.provide(source=HandleProjectMemberInvitationRequestedHandler)
    provider.provide(source=HandleParticipantApprovalRequestedHandler)
    provider.provide(source=HandleResourceApprovalRequestedHandler)
    provider.provide(source=HandleShiftReminderRequestedHandler)
    provider.provide(source=ConfirmProjectInvitationByTokenHandler)
    provider.provide(source=ConfirmReservationByTokenHandler)
    provider.provide(source=ReserveAvailabilityHandler)
    provider.provide(source=ReserveParticipantAvailabilityHandler)
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
    provider.provide(source=GetDescriptionHandler)
    provider.provide(source=GetUserByEmailHandler)
    provider.provide(source=GetUserExistsHandler)
    provider.provide(source=ProvideShiftReportSnapshotHandler)
    provider.provide(source=ListMicrofonFreeTimesHandler)
    provider.provide(source=ListCameraFreeTimesHandler)
    provider.provide(source=ListCameraTripodFreeTimesHandler)
    provider.provide(source=ListLightFreeTimesHandler)
    provider.provide(source=ListLightTripodFreeTimesHandler)
    provider.provide(source=ListSoundFreeTimesHandler)
    provider.provide(source=ListRequisiteFreeTimesHandler)
    provider.provide(source=ListUserSpareTimesHandler)
    provider.provide(source=GetUserSpareTimeHandler)
    provider.provide(source=UpdateCameraHandler)
    provider.provide(source=UpdateCameraTripodHandler)
    provider.provide(source=UpdateDescriptionHandler)
    provider.provide(source=UpdateSpareTimeHandler)
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
