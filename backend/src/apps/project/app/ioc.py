from collections.abc import Iterable

from dishka import Provider, Scope
from faststream.rabbit import RabbitBroker
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.commands import (
    ApproveResourceRequestHandler,
    ApproveShiftHandler,
    ChangeProjectMemberRoleHandler,
    ConfirmShiftParticipantHandler,
    CreateProjectHandler,
    CreateResourceRequestHandler,
    CreateShiftHandler,
    DeclineShiftParticipantHandler,
    InviteProjectMemberHandler,
    InviteShiftParticipantHandler,
    RejectResourceRequestHandler,
    UploadShiftDocumentHandler,
)
from app.application.ports.broker import EventPublisher
from app.application.ports.domain import (
    ClockPort,
    DocumentRepository,
    DocumentStoragePort,
    IdGeneratorPort,
    ProjectMemberRepository,
    ProjectRepository,
    ResourceRequestRepository,
    ShiftParticipantRepository,
    ShiftRepository,
    UserServicePort,
)
from app.application.ports.transaction import TransactionManager
from app.application.queries.documents import GetDocumentDownloadUrlHandler
from app.application.queries.health import HealthHandler
from app.application.support import SystemClock
from app.config import (
    DatabaseSettings,
    Log,
    Minio,
    Rabbitmq,
    SQLAlchemySettings,
    UserService,
)
from app.domain.policy import ActiveMemberPolicy, DirectorMemberPolicy
from app.domain.services import (
    DocumentService,
    ProjectMembershipService,
    ResourceRequestService,
    ShiftParticipantService,
    ShiftService,
)
from app.domain.specification import (
    EditableShiftSpecification,
    IntervalWithinShiftSpecification,
)
from app.infrastructure.adapters.domain_repositories import (
    SqlAlchemyDocumentRepository,
    SqlAlchemyProjectMemberRepository,
    SqlAlchemyProjectRepository,
    SqlAlchemyResourceRequestRepository,
    SqlAlchemyShiftParticipantRepository,
    SqlAlchemyShiftRepository,
)
from app.infrastructure.broker.publisher import RabbitPublisher
from app.infrastructure.database import get_engine, get_session, get_sessionmaker
from app.infrastructure.generation import GenerationUUID
from app.infrastructure.storage.minio import MinioDocumentStorage
from app.infrastructure.transactions import TransactionManagerAlchemy
from app.presentation.http.user_service import UserServiceHttpClient


def make_director_member_policy(
    active_member_policy: ActiveMemberPolicy,
) -> DirectorMemberPolicy:
    return DirectorMemberPolicy(active_member_policy=active_member_policy)


def settings_provider() -> Provider:
    provider = Provider(scope=Scope.APP)
    provider.from_context(provides=Log)
    provider.from_context(provides=DatabaseSettings)
    provider.from_context(provides=SQLAlchemySettings)
    provider.from_context(provides=Rabbitmq)
    provider.from_context(provides=RabbitBroker)
    provider.from_context(provides=UserService)
    provider.from_context(provides=Minio)
    return provider


def db_provider() -> Provider:
    provider = Provider(scope=Scope.REQUEST)
    provider.provide(get_engine, scope=Scope.APP)
    provider.provide(get_sessionmaker, scope=Scope.APP)
    provider.provide(get_session, provides=AsyncSession)
    return provider


def adapters_provider() -> Provider:
    provider = Provider(scope=Scope.REQUEST)
    provider.provide(source=TransactionManagerAlchemy, provides=TransactionManager)
    provider.provide(source=GenerationUUID, provides=IdGeneratorPort, scope=Scope.APP)
    provider.provide(source=RabbitPublisher, provides=EventPublisher)
    provider.provide(source=UserServiceHttpClient, provides=UserServicePort, scope=Scope.APP)
    provider.provide(
        source=MinioDocumentStorage,
        provides=DocumentStoragePort,
        scope=Scope.APP,
    )
    provider.provide(source=SqlAlchemyProjectRepository, provides=ProjectRepository)
    provider.provide(source=SqlAlchemyProjectMemberRepository, provides=ProjectMemberRepository)
    provider.provide(source=SqlAlchemyShiftRepository, provides=ShiftRepository)
    provider.provide(
        source=SqlAlchemyShiftParticipantRepository, provides=ShiftParticipantRepository
    )
    provider.provide(source=SqlAlchemyDocumentRepository, provides=DocumentRepository)
    provider.provide(source=SqlAlchemyResourceRequestRepository, provides=ResourceRequestRepository)
    return provider


def domain_services_provider() -> Provider:
    provider = Provider(scope=Scope.APP)
    provider.provide(source=ActiveMemberPolicy)
    provider.provide(source=make_director_member_policy, provides=DirectorMemberPolicy)
    provider.provide(source=EditableShiftSpecification)
    provider.provide(source=IntervalWithinShiftSpecification)
    provider.provide(source=ProjectMembershipService)
    provider.provide(source=ShiftService)
    provider.provide(source=ShiftParticipantService)
    provider.provide(source=DocumentService)
    provider.provide(source=ResourceRequestService)
    provider.provide(source=SystemClock, provides=ClockPort)
    return provider


def use_case_provider() -> Provider:
    provider = Provider(scope=Scope.REQUEST)
    provider.provide(source=HealthHandler)
    provider.provide(source=GetDocumentDownloadUrlHandler)
    provider.provide(source=CreateProjectHandler)
    provider.provide(source=InviteProjectMemberHandler)
    provider.provide(source=ChangeProjectMemberRoleHandler)
    provider.provide(source=CreateShiftHandler)
    provider.provide(source=ApproveShiftHandler)
    provider.provide(source=InviteShiftParticipantHandler)
    provider.provide(source=ConfirmShiftParticipantHandler)
    provider.provide(source=DeclineShiftParticipantHandler)
    provider.provide(source=UploadShiftDocumentHandler)
    provider.provide(source=CreateResourceRequestHandler)
    provider.provide(source=ApproveResourceRequestHandler)
    provider.provide(source=RejectResourceRequestHandler)
    return provider


def setup_providers() -> Iterable[Provider]:
    return (
        settings_provider(),
        db_provider(),
        adapters_provider(),
        domain_services_provider(),
        use_case_provider(),
    )
