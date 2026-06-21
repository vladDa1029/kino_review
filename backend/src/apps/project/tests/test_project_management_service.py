import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from app.application.commands.participants import (
    ConfirmShiftParticipantCommand,
    ConfirmShiftParticipantHandler,
    InviteShiftParticipantCommand,
    InviteShiftParticipantHandler,
)
from app.application.commands.projects import (
    ApproveProjectMemberInvitationCommand,
    ApproveProjectMemberInvitationHandler,
    CreateProjectCommand,
    CreateProjectHandler,
    DeleteProjectCommand,
    DeleteProjectHandler,
    InviteProjectMemberByEmailCommand,
    InviteProjectMemberByEmailHandler,
    InviteProjectMemberCommand,
    InviteProjectMemberHandler,
    RemoveProjectMemberCommand,
    RemoveProjectMemberHandler,
    UpdateProjectCommand,
    UpdateProjectHandler,
)
from app.application.commands.reports import (
    ArchiveShiftReportCommand,
    ArchiveShiftReportHandler,
    GenerateShiftReportCommand,
    GenerateShiftReportHandler,
    ProcessShiftReportGenerationCommand,
    ProcessShiftReportGenerationHandler,
)
from app.application.commands.reservation_outbox import ProcessReservationOutboxHandler
from app.application.commands.resources import (
    ApproveResourceRequestCommand,
    ApproveResourceRequestHandler,
    CreateResourceRequestCommand,
    CreateResourceRequestHandler,
)
from app.application.commands.shift_reminders import (
    SHIFT_REMINDER_REQUESTED_TOPIC,
    ProcessShiftRemindersHandler,
    build_reminder_notification_id,
)
from app.application.commands.shifts import (
    ApproveShiftCommand,
    ApproveShiftHandler,
    CancelShiftCommand,
    CancelShiftHandler,
)
from app.application.ports.domain import (
    StoredFile,
    UserIdentity,
    UserResourceItem,
    UserResourceTimeWindow,
)
from app.application.ports.reporting import (
    ShiftReportResourceDetails,
    ShiftReportSnapshot,
    ShiftReportUserDetails,
)
from app.application.ports.tasks import ScheduleShiftReportGenerationCommand
from app.application.queries.documents import (
    GetDocumentDownloadUrlHandler,
    GetDocumentDownloadUrlQuery,
)
from app.application.queries.projects import (
    GetProjectHandler,
    GetProjectQuery,
    ListActorProjectsHandler,
    ListActorProjectsQuery,
)
from app.application.queries.resources import (
    GetProjectMemberHandler,
    GetProjectMemberQuery,
    GetProjectUserResourcesHandler,
    GetProjectUserResourcesQuery,
    ListProjectMembersHandler,
    ListProjectMembersQuery,
)
from app.application.support import SystemClock
from app.config import ShiftReminder as ShiftReminderSettings
from app.domain.entities import (
    Document,
    Project,
    ProjectMember,
    ReservationOutboxMessage,
    Shift,
    ShiftParticipant,
    ShiftReminder,
    ShiftReport,
    ShiftResourceRequest,
)
from app.domain.enums import (
    DocumentStatus,
    DocumentType,
    ProjectMemberStatus,
    ProjectRole,
    ProjectStatus,
    ResourceRequestStatus,
    ShiftParticipantStatus,
    ShiftReminderStatus,
    ShiftReportActualityStatus,
    ShiftReportGenerationStatus,
    ShiftStatus,
)
from app.domain.errors.business import AccessDeniedError, EntityNotFoundError, StateTransitionError
from app.domain.policy.member_access import ActiveMemberPolicy, DirectorMemberPolicy
from app.domain.services import (
    ProjectMembershipService,
    ResourceRequestService,
    ShiftParticipantService,
    ShiftService,
)


def now_utc() -> datetime:
    return datetime.now(tz=UTC)


class FakeTx:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class FakePublisher:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, topic: str, payload: dict) -> None:
        self.events.append((topic, payload))


class FakeUserService:
    def __init__(self, fail_reserve_user: bool = False) -> None:
        self.fail_reserve_user = fail_reserve_user
        self.existing_users: set[UUID] = set()
        self.users_by_email: dict[str, UUID] = {}
        self.resources: dict[tuple[UUID, str], list[UserResourceItem]] = {}
        self.request_ids: list[UUID] = []
        self.cancelled_user_reservations: list[UUID] = []
        self.cancelled_resource_reservations: list[UUID] = []

    async def ensure_user_exists(self, user_id: UUID) -> None:
        self.existing_users.add(user_id)

    async def get_user_by_email(self, email: str) -> UserIdentity:
        user_id = self.users_by_email.get(email)
        if user_id is None:
            raise EntityNotFoundError("User is not found by email.")
        return UserIdentity(user_id=user_id, email=email)

    async def ensure_user_resource_exists(
        self,
        *,
        user_id: UUID,
        resource_kind: str,
        resource_id: UUID,
    ) -> None:
        resources = self.resources.get((user_id, resource_kind), [])
        if not any(resource.resource_id == resource_id for resource in resources):
            raise EntityNotFoundError("Resource is not found for user.")

    async def reserve_user_time(
        self,
        *,
        request_id: UUID,
        user_id: UUID,
        time_from: datetime,
        time_to: datetime,
        project_id: UUID,
        shift_id: UUID,
        entity_id: UUID,
    ) -> None:
        self.request_ids.append(request_id)
        if self.fail_reserve_user:
            raise RuntimeError("reserve failed")
        return None

    async def reserve_resource_time(
        self,
        *,
        request_id: UUID,
        owner_user_id: UUID,
        resource_id: UUID,
        time_from: datetime,
        time_to: datetime,
        project_id: UUID,
        shift_id: UUID,
        entity_id: UUID,
    ) -> None:
        self.request_ids.append(request_id)
        return None

    async def cancel_user_reservation(
        self,
        *,
        request_id: UUID,
        user_id: UUID,
        reservation_id: UUID,
        project_id: UUID,
        shift_id: UUID,
        entity_id: UUID,
    ) -> None:
        self.cancelled_user_reservations.append(reservation_id)
        return None

    async def cancel_resource_reservation(
        self,
        *,
        request_id: UUID,
        owner_user_id: UUID,
        resource_id: UUID,
        reservation_id: UUID,
        project_id: UUID,
        shift_id: UUID,
        entity_id: UUID,
    ) -> None:
        self.cancelled_resource_reservations.append(reservation_id)
        return None

    async def list_user_resources(
        self,
        *,
        user_id: UUID,
        resource_kinds: tuple[str, ...],
    ) -> list[UserResourceItem]:
        result: list[UserResourceItem] = []
        for kind in resource_kinds:
            result.extend(self.resources.get((user_id, kind), []))
        return result


class FakeStorage:
    async def upload(
        self,
        *,
        filename: str,
        content: bytes,
        content_type: str,
        storage_key: str | None = None,
    ) -> StoredFile:
        return StoredFile(
            bucket="bucket",
            storage_key=storage_key or f"key-{filename}",
            size=len(content),
            mime_type=content_type,
        )

    async def get_download_url(self, *, storage_key: str) -> str:
        return f"https://example.local/{storage_key}"


class FakeIdGenerator:
    def __call__(self) -> UUID:
        return uuid4()


class SequenceIdGenerator:
    def __init__(self, values: list[UUID]) -> None:
        self._values = values
        self._index = 0

    def __call__(self) -> UUID:
        if self._index >= len(self._values):
            raise RuntimeError("No IDs left in generator sequence.")
        value = self._values[self._index]
        self._index += 1
        return value


class InMemoryProjectRepo:
    def __init__(self) -> None:
        self.data: dict[UUID, Project] = {}

    async def add(self, project: Project) -> None:
        self.data[project.oid] = project

    async def get_by_id(self, project_id: UUID) -> Project | None:
        return self.data.get(project_id)

    async def list_all(self, *, include_archived: bool = False) -> list[Project]:
        projects = [
            project
            for project in self.data.values()
            if include_archived or project.status != ProjectStatus.ARCHIVED
        ]
        projects.sort(key=lambda item: item.created_at, reverse=True)
        return projects

    async def list_by_user(self, user_id: UUID, *, include_archived: bool = False) -> list[Project]:
        return [
            project
            for project in self.data.values()
            if (project.owner_id == user_id)
            and (include_archived or project.status != ProjectStatus.ARCHIVED)
        ]

    async def update(self, project: Project) -> None:
        self.data[project.oid] = project


class InMemoryProjectMemberRepo:
    def __init__(self) -> None:
        self.data: dict[tuple[UUID, UUID], ProjectMember] = {}

    async def add(self, member: ProjectMember) -> None:
        self.data[(member.project_id, member.user_id)] = member

    async def list_by_project(self, project_id: UUID) -> list[ProjectMember]:
        return [
            member
            for (candidate_project_id, _), member in self.data.items()
            if candidate_project_id == project_id
        ]

    async def get_by_project_and_user(
        self, project_id: UUID, user_id: UUID
    ) -> ProjectMember | None:
        return self.data.get((project_id, user_id))

    async def update(self, member: ProjectMember) -> None:
        self.data[(member.project_id, member.user_id)] = member


class InMemoryShiftRepo:
    def __init__(self) -> None:
        self.data: dict[UUID, Shift] = {}

    async def add(self, shift: Shift) -> None:
        self.data[shift.oid] = shift

    async def get_by_id(self, shift_id: UUID) -> Shift | None:
        return self.data.get(shift_id)

    async def list_by_project(
        self,
        project_id: UUID,
        *,
        include_cancelled: bool = False,
        status_filter: ShiftStatus | None = None,
    ) -> list[Shift]:
        shifts = [shift for shift in self.data.values() if shift.project_id == project_id]
        if status_filter is not None:
            shifts = [shift for shift in shifts if shift.status == status_filter]
        elif not include_cancelled:
            shifts = [shift for shift in shifts if shift.status != ShiftStatus.CANCELLED]
        shifts.sort(key=lambda item: item.start_time, reverse=True)
        return shifts

    async def update(self, shift: Shift) -> None:
        self.data[shift.oid] = shift


class InMemoryParticipantRepo:
    def __init__(self) -> None:
        self.by_id: dict[UUID, ShiftParticipant] = {}
        self.by_shift_user: dict[tuple[UUID, UUID], ShiftParticipant] = {}

    async def add(self, participant: ShiftParticipant) -> None:
        self.by_id[participant.oid] = participant
        self.by_shift_user[(participant.shift_id, participant.user_id)] = participant

    async def get_by_id(self, participant_id: UUID) -> ShiftParticipant | None:
        return self.by_id.get(participant_id)

    async def get_by_shift_and_user(self, shift_id: UUID, user_id: UUID) -> ShiftParticipant | None:
        return self.by_shift_user.get((shift_id, user_id))

    async def list_by_shift(self, shift_id: UUID) -> list[ShiftParticipant]:
        return [item for item in self.by_id.values() if item.shift_id == shift_id]

    async def list_active_by_user(self, user_id: UUID) -> list[ShiftParticipant]:
        active = {
            ShiftParticipantStatus.CONFIRMED,
            ShiftParticipantStatus.RESERVING,
            ShiftParticipantStatus.RESERVED,
        }
        return [
            item
            for item in self.by_id.values()
            if item.user_id == user_id and item.status in active
        ]

    async def update(self, participant: ShiftParticipant) -> None:
        self.by_id[participant.oid] = participant
        self.by_shift_user[(participant.shift_id, participant.user_id)] = participant


class InMemoryDocumentRepo:
    def __init__(self) -> None:
        self.data: dict[UUID, Document] = {}

    async def add(self, document: Document) -> None:
        self.data[document.oid] = document

    async def get_by_id(self, document_id: UUID) -> Document | None:
        return self.data.get(document_id)

    async def list_by_shift(self, shift_id: UUID) -> list[Document]:
        return [
            document
            for document in self.data.values()
            if document.shift_id == shift_id
        ]

    async def update(self, document: Document) -> None:
        self.data[document.oid] = document


class InMemoryResourceRequestRepo:
    def __init__(self) -> None:
        self.data: dict[UUID, ShiftResourceRequest] = {}

    async def add(self, request: ShiftResourceRequest) -> None:
        self.data[request.oid] = request

    async def get_by_id(self, request_id: UUID) -> ShiftResourceRequest | None:
        return self.data.get(request_id)

    async def list_by_shift(self, shift_id: UUID) -> list[ShiftResourceRequest]:
        return [item for item in self.data.values() if item.shift_id == shift_id]

    async def update(self, request: ShiftResourceRequest) -> None:
        self.data[request.oid] = request


class InMemoryReservationOutboxRepo:
    def __init__(self) -> None:
        self.data: dict[UUID, ReservationOutboxMessage] = {}

    async def add(self, message: ReservationOutboxMessage) -> None:
        self.data[message.oid] = message

    async def get_by_id(self, message_id: UUID) -> ReservationOutboxMessage | None:
        return self.data.get(message_id)

    async def list_pending(self, *, limit: int) -> list[ReservationOutboxMessage]:
        pending = [
            message for message in self.data.values() if message.status == "pending"
        ]
        pending.sort(key=lambda item: item.created_at)
        return pending[:limit]

    async def update(self, message: ReservationOutboxMessage) -> None:
        self.data[message.oid] = message


class InMemoryShiftReminderRepo:
    def __init__(self) -> None:
        self.data: dict[UUID, ShiftReminder] = {}

    async def add(self, reminder: ShiftReminder) -> None:
        self.data[reminder.oid] = reminder

    async def get_by_id(self, reminder_id: UUID) -> ShiftReminder | None:
        return self.data.get(reminder_id)

    async def get_by_shift(self, shift_id: UUID) -> ShiftReminder | None:
        for reminder in self.data.values():
            if reminder.shift_id == shift_id:
                return reminder
        return None

    async def list_due(self, *, now: datetime, limit: int) -> list[ShiftReminder]:
        due = [
            reminder
            for reminder in self.data.values()
            if reminder.status == ShiftReminderStatus.PENDING and reminder.fire_at <= now
        ]
        due.sort(key=lambda item: item.fire_at)
        return due[:limit]

    async def update(self, reminder: ShiftReminder) -> None:
        self.data[reminder.oid] = reminder


class InMemoryShiftReportRepo:
    def __init__(self) -> None:
        self.data: dict[UUID, ShiftReport] = {}

    async def add(self, report: ShiftReport) -> None:
        self.data[report.oid] = report

    async def get_by_id(self, report_id: UUID) -> ShiftReport | None:
        return self.data.get(report_id)

    async def list_by_shift(self, shift_id: UUID) -> list[ShiftReport]:
        reports = [report for report in self.data.values() if report.shift_id == shift_id]
        reports.sort(key=lambda item: item.version)
        return reports

    async def update(self, report: ShiftReport) -> None:
        self.data[report.oid] = report


class FakeShiftReportTaskDispatcher:
    def __init__(self) -> None:
        self.commands: list[ScheduleShiftReportGenerationCommand] = []

    async def schedule_generation(self, command: ScheduleShiftReportGenerationCommand) -> None:
        self.commands.append(command)


class FakeShiftReportSnapshot:
    def __init__(self, *, fail: Exception | None = None) -> None:
        self.fail = fail
        self.calls: list[dict[str, object]] = []
        self.snapshot = ShiftReportSnapshot(users=(), resources=())

    async def fetch_snapshot(
        self,
        *,
        report_id: UUID,
        project_id: UUID,
        shift_id: UUID,
        participants,
        resources,
    ) -> ShiftReportSnapshot:
        self.calls.append(
            {
                "report_id": report_id,
                "project_id": project_id,
                "shift_id": shift_id,
                "participants": participants,
                "resources": resources,
            }
        )
        if self.fail is not None:
            raise self.fail
        return self.snapshot


class FakeShiftReportRenderer:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def render(self, **payload) -> bytes:
        self.calls.append(payload)
        return b"fake-xlsx"


def build_context(
    *,
    fail_reserve_user: bool = False,
    id_generator: FakeIdGenerator | SequenceIdGenerator | None = None,
):
    tx = FakeTx()
    publisher = FakePublisher()
    user_service = FakeUserService(fail_reserve_user=fail_reserve_user)
    projects = InMemoryProjectRepo()
    members = InMemoryProjectMemberRepo()
    shifts = InMemoryShiftRepo()
    participants = InMemoryParticipantRepo()
    documents = InMemoryDocumentRepo()
    requests = InMemoryResourceRequestRepo()
    reservation_outbox = InMemoryReservationOutboxRepo()
    shift_reports = InMemoryShiftReportRepo()
    storage = FakeStorage()
    clock = SystemClock()
    reservation_processor = ProcessReservationOutboxHandler(
        transaction_manager=tx,
        clock=clock,
        publisher=publisher,
        user_service=user_service,
        project_members=members,
        shifts=shifts,
        shift_participants=participants,
        resource_requests=requests,
        reservation_outbox=reservation_outbox,
    )

    create_project_handler = CreateProjectHandler(
        transaction_manager=tx,
        clock=clock,
        id_generator=id_generator or FakeIdGenerator(),
        publisher=publisher,
        projects=projects,
        project_members=members,
        membership_service=ProjectMembershipService(),
    )
    confirm_participant_handler = ConfirmShiftParticipantHandler(
        transaction_manager=tx,
        clock=clock,
        publisher=publisher,
        reservation_outbox=reservation_outbox,
        project_members=members,
        shifts=shifts,
        shift_participants=participants,
        shift_reports=shift_reports,
        shift_participant_service=ShiftParticipantService(),
    )
    get_document_url_handler = GetDocumentDownloadUrlHandler(
        documents=documents,
        shifts=shifts,
        project_members=members,
        document_storage=storage,
    )
    return (
        create_project_handler,
        confirm_participant_handler,
        get_document_url_handler,
        tx,
        publisher,
        user_service,
        projects,
        members,
        shifts,
        participants,
        documents,
        requests,
    )


def test_create_project_commits_and_publishes_event() -> None:
    async def scenario():
        (
            create_project_handler,
            _,
            _,
            tx,
            publisher,
            user_service,
            projects,
            members,
            _,
            _,
            _,
            _,
        ) = build_context()
        owner_id = uuid4()
        project = await create_project_handler(
            CreateProjectCommand(
                owner_id=owner_id,
                title="Project X",
                description="Desc",
            )
        )

        assert tx.commits == 1
        assert tx.rollbacks == 0
        assert project.oid in projects.data
        owner_member = members.data[(project.oid, owner_id)]
        assert owner_member.role == ProjectRole.DIRECTOR
        assert owner_member.status == ProjectMemberStatus.ACTIVE
        assert publisher.events[0][0] == "project.created"
        assert user_service.existing_users == set()

    asyncio.run(scenario())


def test_create_project_uses_injected_id_generator() -> None:
    async def scenario():
        expected_project_id = uuid4()
        expected_member_id = uuid4()
        (
            create_project_handler,
            _,
            _,
            _,
            _,
            _,
            projects,
            members,
            _,
            _,
            _,
            _,
        ) = build_context(
            id_generator=SequenceIdGenerator([expected_project_id, expected_member_id])
        )
        owner_id = uuid4()
        project = await create_project_handler(
            CreateProjectCommand(
                owner_id=owner_id,
                title="Project IDs",
                description="Desc",
            )
        )

        assert project.oid == expected_project_id
        assert project.status == ProjectStatus.ACTIVE
        assert expected_project_id in projects.data
        owner_member = members.data[(expected_project_id, owner_id)]
        assert owner_member.oid == expected_member_id

    asyncio.run(scenario())


def test_invite_project_member_still_checks_invited_user_exists() -> None:
    async def scenario():
        (
            create_project_handler,
            _,
            _,
            tx,
            publisher,
            user_service,
            projects,
            members,
            _,
            _,
            _,
            _,
        ) = build_context()
        owner_id = uuid4()
        invited_user_id = uuid4()
        project = await create_project_handler(
            CreateProjectCommand(
                owner_id=owner_id,
                title="Invite members",
                description="Desc",
            )
        )
        handler = InviteProjectMemberHandler(
            transaction_manager=tx,
            clock=SystemClock(),
            id_generator=FakeIdGenerator(),
            publisher=publisher,
            user_service=user_service,
            project_members=members,
            projects=projects,
            membership_service=ProjectMembershipService(),
        )

        member = await handler(
            InviteProjectMemberCommand(
                project_id=project.oid,
                actor_user_id=owner_id,
                invited_user_id=invited_user_id,
                role=ProjectRole.CAMERA,
            )
        )

        assert member.user_id == invited_user_id
        assert member.status == ProjectMemberStatus.INVITED
        assert invited_user_id in user_service.existing_users
        assert publisher.events[-1][0] == "project.member_invitation_requested"
        assert publisher.events[-1][1]["user_id"] == str(invited_user_id)
        assert publisher.events[-1][1]["project_title"] == "Invite members"

    asyncio.run(scenario())


def test_invite_project_member_can_resolve_invitee_by_email() -> None:
    async def scenario():
        (
            create_project_handler,
            _,
            _,
            tx,
            publisher,
            user_service,
            projects,
            members,
            _,
            _,
            _,
            _,
        ) = build_context()
        owner_id = uuid4()
        invited_user_id = uuid4()
        invitee_email = "invitee@example.com"
        user_service.users_by_email[invitee_email] = invited_user_id
        project = await create_project_handler(
            CreateProjectCommand(
                owner_id=owner_id,
                title="Email invite project",
                description="Desc",
            )
        )
        handler = InviteProjectMemberByEmailHandler(
            transaction_manager=tx,
            clock=SystemClock(),
            id_generator=FakeIdGenerator(),
            publisher=publisher,
            user_service=user_service,
            project_members=members,
            projects=projects,
            membership_service=ProjectMembershipService(),
        )

        member = await handler(
            InviteProjectMemberByEmailCommand(
                project_id=project.oid,
                actor_user_id=owner_id,
                email=invitee_email,
                role=ProjectRole.ACTOR,
            )
        )

        assert member.user_id == invited_user_id
        assert member.status == ProjectMemberStatus.INVITED
        assert invited_user_id not in user_service.existing_users
        invite_event = publisher.events[-1]
        assert invite_event[0] == "project.member_invitation_requested"
        assert invite_event[1]["request_id"] == str(member.oid)
        assert invite_event[1]["project_id"] == str(project.oid)
        assert invite_event[1]["project_title"] == "Email invite project"
        assert invite_event[1]["user_id"] == str(invited_user_id)
        assert invite_event[1]["role"] == "ACTOR"

    asyncio.run(scenario())


def test_invite_shift_participant_still_checks_participant_user_exists() -> None:
    async def scenario():
        (
            create_project_handler,
            _,
            _,
            tx,
            publisher,
            user_service,
            _,
            members,
            shifts,
            participants,
            _,
            _,
        ) = build_context()
        owner_id = uuid4()
        participant_user_id = uuid4()
        project = await create_project_handler(
            CreateProjectCommand(
                owner_id=owner_id,
                title="Invite participants",
                description="Desc",
            )
        )
        now = now_utc()
        shift = Shift(
            oid=uuid4(),
            project_id=project.oid,
            title="Morning shift",
            description="Desc",
            start_time=now,
            end_time=now + timedelta(hours=3),
            status=ShiftStatus.DRAFT,
            created_by=owner_id,
            created_at=now,
            updated_at=now,
        )
        await shifts.add(shift)
        await members.add(
            ProjectMember(
                oid=uuid4(),
                project_id=project.oid,
                user_id=participant_user_id,
                role=ProjectRole.ACTOR,
                status=ProjectMemberStatus.ACTIVE,
                invited_by=owner_id,
                created_at=now,
                updated_at=now,
            )
        )
        handler = InviteShiftParticipantHandler(
            transaction_manager=tx,
            clock=SystemClock(),
            id_generator=FakeIdGenerator(),
            publisher=publisher,
            user_service=user_service,
            project_members=members,
            shifts=shifts,
            shift_participants=participants,
            shift_reports=InMemoryShiftReportRepo(),
            shift_participant_service=ShiftParticipantService(),
        )

        participant = await handler(
            InviteShiftParticipantCommand(
                shift_id=shift.oid,
                actor_user_id=owner_id,
                participant_user_id=participant_user_id,
                role=ProjectRole.CAMERA,
                time_from=now + timedelta(minutes=15),
                time_to=now + timedelta(hours=1),
            )
        )

        assert participant.user_id == participant_user_id
        assert participant.status == ShiftParticipantStatus.INVITED
        assert participant_user_id in user_service.existing_users

    asyncio.run(scenario())


def test_delete_project_archives_and_publishes_event() -> None:
    async def scenario():
        (
            create_project_handler,
            _,
            _,
            tx,
            publisher,
            _,
            projects,
            members,
            _,
            _,
            _,
            _,
        ) = build_context()
        owner_id = uuid4()
        project = await create_project_handler(
            CreateProjectCommand(
                owner_id=owner_id,
                title="Project for delete",
                description="Desc",
            )
        )
        handler = DeleteProjectHandler(
            transaction_manager=tx,
            clock=SystemClock(),
            publisher=publisher,
            projects=projects,
            project_members=members,
            director_member_policy=DirectorMemberPolicy(),
        )

        archived = await handler(
            DeleteProjectCommand(
                project_id=project.oid,
                actor_user_id=owner_id,
            )
        )

        assert archived.status == ProjectStatus.ARCHIVED
        assert projects.data[project.oid].status == ProjectStatus.ARCHIVED
        assert tx.commits == 2
        assert tx.rollbacks == 0
        assert publisher.events[-1][0] == "project.archived"

    asyncio.run(scenario())


def test_delete_project_denies_non_director() -> None:
    async def scenario():
        (
            _,
            _,
            _,
            tx,
            publisher,
            _,
            projects,
            members,
            _,
            _,
            _,
            _,
        ) = build_context()
        now = now_utc()
        project_id = uuid4()
        director_id = uuid4()
        actor_id = uuid4()
        projects.data[project_id] = Project(
            oid=project_id,
            title="Project",
            description="Desc",
            owner_id=director_id,
            status=ProjectStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        members.data[(project_id, actor_id)] = ProjectMember(
            oid=uuid4(),
            project_id=project_id,
            user_id=actor_id,
            role=ProjectRole.CAMERA,
            status=ProjectMemberStatus.ACTIVE,
            invited_by=director_id,
            created_at=now,
            updated_at=now,
        )
        handler = DeleteProjectHandler(
            transaction_manager=tx,
            clock=SystemClock(),
            publisher=publisher,
            projects=projects,
            project_members=members,
            director_member_policy=DirectorMemberPolicy(),
        )

        with pytest.raises(AccessDeniedError):
            await handler(
                DeleteProjectCommand(
                    project_id=project_id,
                    actor_user_id=actor_id,
                )
            )

        assert projects.data[project_id].status == ProjectStatus.ACTIVE
        assert tx.commits == 0
        assert tx.rollbacks == 1
        assert not any(topic == "project.archived" for topic, _ in publisher.events)

    asyncio.run(scenario())


def test_update_project_by_director() -> None:
    async def scenario():
        (
            create_project_handler,
            _,
            _,
            tx,
            publisher,
            _,
            projects,
            members,
            _,
            _,
            _,
            _,
        ) = build_context()
        owner_id = uuid4()
        project = await create_project_handler(
            CreateProjectCommand(
                owner_id=owner_id,
                title="Old title",
                description="Old description",
            )
        )
        handler = UpdateProjectHandler(
            transaction_manager=tx,
            clock=SystemClock(),
            publisher=publisher,
            projects=projects,
            project_members=members,
            director_member_policy=DirectorMemberPolicy(),
        )

        updated = await handler(
            UpdateProjectCommand(
                project_id=project.oid,
                actor_user_id=owner_id,
                title="New title",
                description="New description",
            )
        )

        assert updated.title == "New title"
        assert updated.description == "New description"
        assert tx.commits == 2
        assert publisher.events[-1][0] == "project.updated"

    asyncio.run(scenario())


def test_update_project_rejects_noop_payload() -> None:
    async def scenario():
        (
            create_project_handler,
            _,
            _,
            tx,
            publisher,
            _,
            projects,
            members,
            _,
            _,
            _,
            _,
        ) = build_context()
        owner_id = uuid4()
        project = await create_project_handler(
            CreateProjectCommand(
                owner_id=owner_id,
                title="Old title",
                description="Old description",
            )
        )
        initial_updated_at = project.updated_at
        initial_events_count = len(publisher.events)
        handler = UpdateProjectHandler(
            transaction_manager=tx,
            clock=SystemClock(),
            publisher=publisher,
            projects=projects,
            project_members=members,
            director_member_policy=DirectorMemberPolicy(),
        )

        with pytest.raises(StateTransitionError):
            await handler(
                UpdateProjectCommand(
                    project_id=project.oid,
                    actor_user_id=owner_id,
                )
            )

        assert tx.commits == 1
        assert tx.rollbacks == 0
        assert projects.data[project.oid].updated_at == initial_updated_at
        assert len(publisher.events) == initial_events_count

    asyncio.run(scenario())


def test_update_project_rejects_blank_title_after_strip() -> None:
    async def scenario():
        (
            create_project_handler,
            _,
            _,
            tx,
            publisher,
            _,
            projects,
            members,
            _,
            _,
            _,
            _,
        ) = build_context()
        owner_id = uuid4()
        project = await create_project_handler(
            CreateProjectCommand(
                owner_id=owner_id,
                title="Initial title",
                description="Initial description",
            )
        )
        initial_title = project.title
        initial_events_count = len(publisher.events)
        handler = UpdateProjectHandler(
            transaction_manager=tx,
            clock=SystemClock(),
            publisher=publisher,
            projects=projects,
            project_members=members,
            director_member_policy=DirectorMemberPolicy(),
        )

        with pytest.raises(StateTransitionError):
            await handler(
                UpdateProjectCommand(
                    project_id=project.oid,
                    actor_user_id=owner_id,
                    title="   ",
                )
            )

        assert tx.commits == 1
        assert tx.rollbacks == 1
        assert projects.data[project.oid].title == initial_title
        assert len(publisher.events) == initial_events_count

    asyncio.run(scenario())


def test_remove_project_member_marks_removed() -> None:
    async def scenario():
        (
            _,
            _,
            _,
            tx,
            publisher,
            _,
            projects,
            members,
            _,
            _,
            _,
            _,
        ) = build_context()
        now = now_utc()
        project_id = uuid4()
        director_id = uuid4()
        target_user_id = uuid4()
        projects.data[project_id] = Project(
            oid=project_id,
            title="Project",
            description="Desc",
            owner_id=director_id,
            status=ProjectStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        members.data[(project_id, director_id)] = ProjectMember(
            oid=uuid4(),
            project_id=project_id,
            user_id=director_id,
            role=ProjectRole.DIRECTOR,
            status=ProjectMemberStatus.ACTIVE,
            invited_by=director_id,
            created_at=now,
            updated_at=now,
        )
        members.data[(project_id, target_user_id)] = ProjectMember(
            oid=uuid4(),
            project_id=project_id,
            user_id=target_user_id,
            role=ProjectRole.CAMERA,
            status=ProjectMemberStatus.ACTIVE,
            invited_by=director_id,
            created_at=now,
            updated_at=now,
        )
        handler = RemoveProjectMemberHandler(
            transaction_manager=tx,
            clock=SystemClock(),
            publisher=publisher,
            projects=projects,
            project_members=members,
            membership_service=ProjectMembershipService(),
        )

        removed = await handler(
            RemoveProjectMemberCommand(
                project_id=project_id,
                actor_user_id=director_id,
                target_user_id=target_user_id,
            )
        )

        assert removed.status == ProjectMemberStatus.REMOVED
        assert tx.commits == 1
        assert publisher.events[-1][0] == "project.member_removed"

    asyncio.run(scenario())


def test_confirm_participant_moves_to_reserving_and_leaves_processing_to_outbox() -> None:
    async def scenario():
        (
            _,
            confirm_participant_handler,
            _,
            tx,
            _,
            _,
            _,
            members,
            shifts,
            participants,
            _,
            _,
        ) = build_context()
        now = now_utc()
        project_id = uuid4()
        director_id = uuid4()
        participant_user_id = uuid4()
        members.data[(project_id, director_id)] = ProjectMember(
            oid=uuid4(),
            project_id=project_id,
            user_id=director_id,
            role=ProjectRole.DIRECTOR,
            status=ProjectMemberStatus.ACTIVE,
            invited_by=director_id,
            created_at=now,
            updated_at=now,
        )
        members.data[(project_id, participant_user_id)] = ProjectMember(
            oid=uuid4(),
            project_id=project_id,
            user_id=participant_user_id,
            role=ProjectRole.CAMERA,
            status=ProjectMemberStatus.ACTIVE,
            invited_by=director_id,
            created_at=now,
            updated_at=now,
        )
        shift = Shift(
            oid=uuid4(),
            project_id=project_id,
            title="S",
            description="D",
            start_time=now,
            end_time=now + timedelta(hours=3),
            status=ShiftStatus.DRAFT,
            created_by=director_id,
            created_at=now,
            updated_at=now,
        )
        shifts.data[shift.oid] = shift
        participant = ShiftParticipant(
            oid=uuid4(),
            shift_id=shift.oid,
            user_id=participant_user_id,
            role=ProjectRole.CAMERA,
            time_from=now + timedelta(minutes=5),
            time_to=now + timedelta(hours=1),
            status=ShiftParticipantStatus.INVITED,
            added_by=director_id,
            created_at=now,
            updated_at=now,
        )
        await participants.add(participant)

        updated = await confirm_participant_handler(
            ConfirmShiftParticipantCommand(
                participant_id=participant.oid,
                actor_user_id=participant_user_id,
            )
        )

        assert updated is not None
        assert updated.status == ShiftParticipantStatus.RESERVING
        assert tx.commits == 1
        assert tx.rollbacks == 0

    asyncio.run(scenario())


def test_get_document_download_url_query_returns_url() -> None:
    async def scenario():
        (
            _,
            _,
            get_document_url_handler,
            _,
            _,
            _,
            _,
            members,
            shifts,
            _,
            documents,
            _,
        ) = build_context()
        now = now_utc()
        project_id = uuid4()
        user_id = uuid4()
        members.data[(project_id, user_id)] = ProjectMember(
            oid=uuid4(),
            project_id=project_id,
            user_id=user_id,
            role=ProjectRole.DIRECTOR,
            status=ProjectMemberStatus.ACTIVE,
            invited_by=user_id,
            created_at=now,
            updated_at=now,
        )
        shift = Shift(
            oid=uuid4(),
            project_id=project_id,
            title="S",
            description="D",
            start_time=now,
            end_time=now + timedelta(hours=2),
            status=ShiftStatus.DRAFT,
            created_by=user_id,
            created_at=now,
            updated_at=now,
        )
        shifts.data[shift.oid] = shift
        document = Document(
            oid=uuid4(),
            shift_id=shift.oid,
            doc_type=DocumentType.PLAN,
            filename="callsheet.pdf",
            title="Callsheet",
            storage_key="key-callsheet.pdf",
            bucket="bucket",
            mime_type="application/pdf",
            size=128,
            owner_id=user_id,
            description=None,
            version=1,
            status=DocumentStatus.ACTIVE,
            created_at=now,
        )
        documents.data[document.oid] = document

        url = await get_document_url_handler(
            GetDocumentDownloadUrlQuery(
                document_id=document.oid,
                actor_user_id=user_id,
            )
        )

        assert url == "https://example.local/key-callsheet.pdf"

    asyncio.run(scenario())


def test_approve_project_member_invitation_activates_and_publishes_event() -> None:
    async def scenario():
        (
            _,
            _,
            _,
            tx,
            publisher,
            _,
            _,
            members,
            _,
            _,
            _,
            _,
        ) = build_context()
        now = now_utc()
        project_id = uuid4()
        user_id = uuid4()
        members.data[(project_id, user_id)] = ProjectMember(
            oid=uuid4(),
            project_id=project_id,
            user_id=user_id,
            role=ProjectRole.CAMERA,
            status=ProjectMemberStatus.INVITED,
            invited_by=uuid4(),
            created_at=now,
            updated_at=now,
        )
        handler = ApproveProjectMemberInvitationHandler(
            transaction_manager=tx,
            clock=SystemClock(),
            publisher=publisher,
            project_members=members,
            membership_service=ProjectMembershipService(),
        )

        member = await handler(
            ApproveProjectMemberInvitationCommand(
                project_id=project_id,
                user_id=user_id,
                approved_by_user_id=user_id,
            )
        )

        assert member is not None
        assert member.status == ProjectMemberStatus.ACTIVE
        assert tx.commits == 1
        assert publisher.events[-1][0] == "project.member_activated"

    asyncio.run(scenario())


def test_get_project_user_resources_query_by_actor_role() -> None:
    async def scenario():
        (
            _,
            _,
            _,
            _,
            _,
            user_service,
            _,
            members,
            _,
            _,
            _,
            _,
        ) = build_context()
        now = now_utc()
        project_id = uuid4()
        director_id = uuid4()
        camera_user_id = uuid4()

        members.data[(project_id, director_id)] = ProjectMember(
            oid=uuid4(),
            project_id=project_id,
            user_id=director_id,
            role=ProjectRole.DIRECTOR,
            status=ProjectMemberStatus.ACTIVE,
            invited_by=director_id,
            created_at=now,
            updated_at=now,
        )
        members.data[(project_id, camera_user_id)] = ProjectMember(
            oid=uuid4(),
            project_id=project_id,
            user_id=camera_user_id,
            role=ProjectRole.CAMERA,
            status=ProjectMemberStatus.ACTIVE,
            invited_by=director_id,
            created_at=now,
            updated_at=now,
        )

        user_service.resources[(camera_user_id, "cameras")] = [
            UserResourceItem(
                resource_kind="cameras",
                resource_id=uuid4(),
                title="Sony",
                description="Camera",
                resource_type="mirrorless",
                size=None,
                created_at=now,
                windows=(
                    UserResourceTimeWindow(
                        window_id=uuid4(),
                        start_time=now + timedelta(hours=1),
                        end_time=now + timedelta(hours=2),
                        status="free",
                    ),
                    UserResourceTimeWindow(
                        window_id=uuid4(),
                        start_time=now + timedelta(hours=3),
                        end_time=now + timedelta(hours=4),
                        status="reserved",
                    ),
                ),
            )
        ]

        handler = GetProjectUserResourcesHandler(
            project_members=members,
            user_service=user_service,
            active_member_policy=ActiveMemberPolicy(),
        )
        result = await handler(
            GetProjectUserResourcesQuery(
                project_id=project_id,
                actor_user_id=director_id,
                target_user_id=camera_user_id,
            )
        )

        assert result.user_id == camera_user_id
        assert result.role == ProjectRole.CAMERA
        assert len(result.resources) == 1
        assert result.resources[0].resource_kind == "cameras"
        assert len(result.resources[0].windows) == 2

    asyncio.run(scenario())


def test_get_project_user_resources_query_denies_role_without_access() -> None:
    async def scenario():
        (
            _,
            _,
            _,
            _,
            _,
            user_service,
            _,
            members,
            _,
            _,
            _,
            _,
        ) = build_context()
        now = now_utc()
        project_id = uuid4()
        actor_user_id = uuid4()
        target_user_id = uuid4()
        members.data[(project_id, actor_user_id)] = ProjectMember(
            oid=uuid4(),
            project_id=project_id,
            user_id=actor_user_id,
            role=ProjectRole.ACTOR,
            status=ProjectMemberStatus.ACTIVE,
            invited_by=uuid4(),
            created_at=now,
            updated_at=now,
        )
        members.data[(project_id, target_user_id)] = ProjectMember(
            oid=uuid4(),
            project_id=project_id,
            user_id=target_user_id,
            role=ProjectRole.CAMERA,
            status=ProjectMemberStatus.ACTIVE,
            invited_by=uuid4(),
            created_at=now,
            updated_at=now,
        )
        handler = GetProjectUserResourcesHandler(
            project_members=members,
            user_service=user_service,
            active_member_policy=ActiveMemberPolicy(),
        )

        with pytest.raises(AccessDeniedError):
            await handler(
                GetProjectUserResourcesQuery(
                    project_id=project_id,
                    actor_user_id=actor_user_id,
                    target_user_id=target_user_id,
                )
            )

    asyncio.run(scenario())


def test_list_project_members_query_returns_active_members_with_oid() -> None:
    async def scenario():
        (
            _,
            _,
            _,
            _,
            _,
            _,
            _,
            members,
            _,
            _,
            _,
            _,
        ) = build_context()
        now = now_utc()
        project_id = uuid4()
        director_id = uuid4()
        camera_user_id = uuid4()
        members.data[(project_id, director_id)] = ProjectMember(
            oid=uuid4(),
            project_id=project_id,
            user_id=director_id,
            role=ProjectRole.DIRECTOR,
            status=ProjectMemberStatus.ACTIVE,
            invited_by=director_id,
            created_at=now,
            updated_at=now,
        )
        members.data[(project_id, camera_user_id)] = ProjectMember(
            oid=uuid4(),
            project_id=project_id,
            user_id=camera_user_id,
            role=ProjectRole.CAMERA,
            status=ProjectMemberStatus.ACTIVE,
            invited_by=director_id,
            created_at=now,
            updated_at=now,
        )

        handler = ListProjectMembersHandler(
            project_members=members,
            active_member_policy=ActiveMemberPolicy(),
        )
        result = await handler(
            ListProjectMembersQuery(
                project_id=project_id,
                actor_user_id=director_id,
                user_id=camera_user_id,
            )
        )

        assert len(result) == 1
        assert result[0].oid is not None
        assert result[0].user_id == camera_user_id
        assert result[0].role == ProjectRole.CAMERA

    asyncio.run(scenario())


def test_get_project_member_query_not_found_for_inactive_without_flag() -> None:
    async def scenario():
        (
            _,
            _,
            _,
            _,
            _,
            _,
            _,
            members,
            _,
            _,
            _,
            _,
        ) = build_context()
        now = now_utc()
        project_id = uuid4()
        director_id = uuid4()
        invited_id = uuid4()
        members.data[(project_id, director_id)] = ProjectMember(
            oid=uuid4(),
            project_id=project_id,
            user_id=director_id,
            role=ProjectRole.DIRECTOR,
            status=ProjectMemberStatus.ACTIVE,
            invited_by=director_id,
            created_at=now,
            updated_at=now,
        )
        members.data[(project_id, invited_id)] = ProjectMember(
            oid=uuid4(),
            project_id=project_id,
            user_id=invited_id,
            role=ProjectRole.CAMERA,
            status=ProjectMemberStatus.INVITED,
            invited_by=director_id,
            created_at=now,
            updated_at=now,
        )
        handler = GetProjectMemberHandler(
            project_members=members,
            active_member_policy=ActiveMemberPolicy(),
        )

        with pytest.raises(EntityNotFoundError):
            await handler(
                GetProjectMemberQuery(
                    project_id=project_id,
                    actor_user_id=director_id,
                    target_user_id=invited_id,
                )
            )

        with_inactive = await handler(
            GetProjectMemberQuery(
                project_id=project_id,
                actor_user_id=director_id,
                target_user_id=invited_id,
                include_inactive=True,
            )
        )
        assert with_inactive.user_id == invited_id
        assert with_inactive.status == int(ProjectMemberStatus.INVITED)

    asyncio.run(scenario())


def test_list_actor_projects_query() -> None:
    async def scenario():
        (
            _,
            _,
            _,
            _,
            _,
            _,
            projects,
            _,
            _,
            _,
            _,
            _,
        ) = build_context()
        actor_id = uuid4()
        other_id = uuid4()
        now = now_utc()
        active_project = Project(
            oid=uuid4(),
            title="Active",
            description="Desc",
            owner_id=actor_id,
            status=ProjectStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        archived_project = Project(
            oid=uuid4(),
            title="Archived",
            description="Desc",
            owner_id=actor_id,
            status=ProjectStatus.ARCHIVED,
            created_at=now,
            updated_at=now,
        )
        other_project = Project(
            oid=uuid4(),
            title="Other",
            description="Desc",
            owner_id=other_id,
            status=ProjectStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await projects.add(active_project)
        await projects.add(archived_project)
        await projects.add(other_project)

        handler = ListActorProjectsHandler(projects=projects)
        result = await handler(ListActorProjectsQuery(actor_user_id=actor_id))
        assert len(result) == 1
        assert result[0].oid == active_project.oid

        result_with_archived = await handler(
            ListActorProjectsQuery(actor_user_id=actor_id, include_archived=True)
        )
        assert len(result_with_archived) == 2

    asyncio.run(scenario())


def test_get_project_query_requires_active_member() -> None:
    async def scenario():
        (
            _,
            _,
            _,
            _,
            _,
            _,
            projects,
            members,
            _,
            _,
            _,
            _,
        ) = build_context()
        now = now_utc()
        project_id = uuid4()
        director_id = uuid4()
        project = Project(
            oid=project_id,
            title="Active",
            description="Desc",
            owner_id=director_id,
            status=ProjectStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await projects.add(project)
        members.data[(project_id, director_id)] = ProjectMember(
            oid=uuid4(),
            project_id=project_id,
            user_id=director_id,
            role=ProjectRole.DIRECTOR,
            status=ProjectMemberStatus.ACTIVE,
            invited_by=director_id,
            created_at=now,
            updated_at=now,
        )

        handler = GetProjectHandler(
            projects=projects,
            project_members=members,
            active_member_policy=ActiveMemberPolicy(),
        )
        result = await handler(
            GetProjectQuery(
                project_id=project_id,
                actor_user_id=director_id,
            )
        )
        assert result.oid == project_id

    asyncio.run(scenario())


def build_report_generation_context():
    tx = FakeTx()
    publisher = FakePublisher()
    projects = InMemoryProjectRepo()
    members = InMemoryProjectMemberRepo()
    shifts = InMemoryShiftRepo()
    participants = InMemoryParticipantRepo()
    requests = InMemoryResourceRequestRepo()
    reports = InMemoryShiftReportRepo()
    storage = FakeStorage()
    snapshot = FakeShiftReportSnapshot()
    renderer = FakeShiftReportRenderer()
    dispatcher = FakeShiftReportTaskDispatcher()
    clock = SystemClock()
    id_generator = FakeIdGenerator()

    generate_handler = GenerateShiftReportHandler(
        transaction_manager=tx,
        clock=clock,
        id_generator=id_generator,
        project_members=members,
        shifts=shifts,
        shift_reports=reports,
        task_dispatcher=dispatcher,
        director_member_policy=DirectorMemberPolicy(),
    )
    process_handler = ProcessShiftReportGenerationHandler(
        transaction_manager=tx,
        clock=clock,
        projects=projects,
        project_members=members,
        shifts=shifts,
        shift_participants=participants,
        resource_requests=requests,
        shift_reports=reports,
        shift_report_snapshot=snapshot,
        report_renderer=renderer,
        document_storage=storage,
        snapshot_retry_count=2,
        snapshot_retry_delay_seconds=0,
    )
    archive_handler = ArchiveShiftReportHandler(
        transaction_manager=tx,
        clock=clock,
        project_members=members,
        shifts=shifts,
        shift_reports=reports,
        director_member_policy=DirectorMemberPolicy(),
    )

    return {
        "tx": tx,
        "publisher": publisher,
        "projects": projects,
        "members": members,
        "shifts": shifts,
        "participants": participants,
        "requests": requests,
        "reports": reports,
        "storage": storage,
        "snapshot": snapshot,
        "renderer": renderer,
        "dispatcher": dispatcher,
        "generate_handler": generate_handler,
        "process_handler": process_handler,
        "archive_handler": archive_handler,
    }


def test_generate_shift_report_creates_pending_version_and_schedules_task() -> None:
    async def scenario() -> None:
        ctx = build_report_generation_context()
        now = now_utc()
        director_id = uuid4()
        project_id = uuid4()
        shift_id = uuid4()

        await ctx["projects"].add(
            Project(
                oid=project_id,
                title="Reports",
                description="Desc",
                owner_id=director_id,
                status=ProjectStatus.ACTIVE,
                created_at=now,
                updated_at=now,
            )
        )
        await ctx["shifts"].add(
            Shift(
                oid=shift_id,
                project_id=project_id,
                title="Approved shift",
                description="Desc",
                start_time=now,
                end_time=now + timedelta(hours=2),
                status=ShiftStatus.APPROVED,
                created_by=director_id,
                approved_by=director_id,
                approved_at=now,
                created_at=now,
                updated_at=now,
            )
        )
        await ctx["members"].add(
            ProjectMember(
                oid=uuid4(),
                project_id=project_id,
                user_id=director_id,
                role=ProjectRole.DIRECTOR,
                status=ProjectMemberStatus.ACTIVE,
                invited_by=director_id,
                created_at=now,
                updated_at=now,
            )
        )

        report = await ctx["generate_handler"](
            GenerateShiftReportCommand(
                shift_id=shift_id,
                actor_user_id=director_id,
            )
        )

        assert report.version == 1
        assert report.generation_status == ShiftReportGenerationStatus.PENDING
        assert ctx["dispatcher"].commands[0].report_id == report.oid
        assert await ctx["reports"].get_by_id(report.oid) is not None

    asyncio.run(scenario())


def test_generate_shift_report_rejects_second_in_progress_report() -> None:
    async def scenario() -> None:
        ctx = build_report_generation_context()
        now = now_utc()
        director_id = uuid4()
        project_id = uuid4()
        shift_id = uuid4()

        await ctx["projects"].add(
            Project(
                oid=project_id,
                title="Reports",
                description="Desc",
                owner_id=director_id,
                status=ProjectStatus.ACTIVE,
                created_at=now,
                updated_at=now,
            )
        )
        await ctx["shifts"].add(
            Shift(
                oid=shift_id,
                project_id=project_id,
                title="Approved shift",
                description="Desc",
                start_time=now,
                end_time=now + timedelta(hours=2),
                status=ShiftStatus.APPROVED,
                created_by=director_id,
                approved_by=director_id,
                approved_at=now,
                created_at=now,
                updated_at=now,
            )
        )
        await ctx["members"].add(
            ProjectMember(
                oid=uuid4(),
                project_id=project_id,
                user_id=director_id,
                role=ProjectRole.DIRECTOR,
                status=ProjectMemberStatus.ACTIVE,
                invited_by=director_id,
                created_at=now,
                updated_at=now,
            )
        )
        await ctx["reports"].add(
            ShiftReport(
                oid=uuid4(),
                project_id=project_id,
                shift_id=shift_id,
                version=1,
                generation_status=ShiftReportGenerationStatus.RENDERING,
                actuality_status=ShiftReportActualityStatus.ACTUAL,
                requested_by_user_id=director_id,
                file_name=None,
                bucket=None,
                storage_key=None,
                mime_type=None,
                generated_at=None,
                archived_at=None,
                error_message=None,
                stale_reason=None,
                stale_marked_at=None,
                created_at=now,
                updated_at=now,
            )
        )

        with pytest.raises(StateTransitionError):
            await ctx["generate_handler"](
                GenerateShiftReportCommand(
                    shift_id=shift_id,
                    actor_user_id=director_id,
                )
            )

    asyncio.run(scenario())


def test_process_shift_report_generation_builds_xlsx_and_marks_report_ready() -> None:
    async def scenario() -> None:
        ctx = build_report_generation_context()
        now = now_utc()
        director_id = uuid4()
        participant_user_id = uuid4()
        external_owner_id = uuid4()
        project_id = uuid4()
        shift_id = uuid4()
        report_id = uuid4()
        resource_id = uuid4()

        await ctx["projects"].add(
            Project(
                oid=project_id,
                title="Feature film",
                description="Desc",
                owner_id=director_id,
                status=ProjectStatus.ACTIVE,
                created_at=now,
                updated_at=now,
            )
        )
        await ctx["shifts"].add(
            Shift(
                oid=shift_id,
                project_id=project_id,
                title="Night shoot",
                description="Desc",
                start_time=now,
                end_time=now + timedelta(hours=4),
                status=ShiftStatus.APPROVED,
                created_by=director_id,
                approved_by=director_id,
                approved_at=now,
                created_at=now,
                updated_at=now,
            )
        )
        await ctx["members"].add(
            ProjectMember(
                oid=uuid4(),
                project_id=project_id,
                user_id=director_id,
                role=ProjectRole.DIRECTOR,
                status=ProjectMemberStatus.ACTIVE,
                invited_by=director_id,
                created_at=now,
                updated_at=now,
            )
        )
        await ctx["members"].add(
            ProjectMember(
                oid=uuid4(),
                project_id=project_id,
                user_id=participant_user_id,
                role=ProjectRole.ACTOR,
                status=ProjectMemberStatus.ACTIVE,
                invited_by=director_id,
                created_at=now,
                updated_at=now,
            )
        )
        await ctx["participants"].add(
            ShiftParticipant(
                oid=uuid4(),
                shift_id=shift_id,
                user_id=participant_user_id,
                role=ProjectRole.ACTOR,
                time_from=now,
                time_to=now + timedelta(hours=2),
                status=ShiftParticipantStatus.RESERVED,
                added_by=director_id,
                created_at=now,
                updated_at=now,
                user_reservation_id=uuid4(),
            )
        )
        await ctx["requests"].add(
            ShiftResourceRequest(
                oid=uuid4(),
                project_id=project_id,
                shift_id=shift_id,
                resource_type="camera",
                resource_id=resource_id,
                resource_owner_user_id=external_owner_id,
                requested_by_user_id=director_id,
                time_from=now,
                time_to=now + timedelta(hours=2),
                status=ResourceRequestStatus.RESERVED,
                created_at=now,
                updated_at=now,
                resource_reservation_id=uuid4(),
            )
        )
        await ctx["reports"].add(
            ShiftReport(
                oid=report_id,
                project_id=project_id,
                shift_id=shift_id,
                version=1,
                generation_status=ShiftReportGenerationStatus.PENDING,
                actuality_status=ShiftReportActualityStatus.ACTUAL,
                requested_by_user_id=director_id,
                file_name=None,
                bucket=None,
                storage_key=None,
                mime_type=None,
                generated_at=None,
                archived_at=None,
                error_message=None,
                stale_reason=None,
                stale_marked_at=None,
                created_at=now,
                updated_at=now,
            )
        )
        ctx["snapshot"].snapshot = ShiftReportSnapshot(
            users=(
                ShiftReportUserDetails(
                    user_id=participant_user_id,
                    username="Ivan Ivanov",
                    phone="+79990001122",
                    email="ivan@example.com",
                ),
                ShiftReportUserDetails(
                    user_id=external_owner_id,
                    username="Owner",
                    phone=None,
                    email="owner@example.com",
                ),
            ),
            resources=(
                ShiftReportResourceDetails(
                    resource_id=resource_id,
                    owner_user_id=external_owner_id,
                    title="Sony A7",
                    resource_type="mirrorless",
                    description="Main camera",
                    size=None,
                ),
            ),
        )

        await ctx["process_handler"](
            ProcessShiftReportGenerationCommand(
                report_id=report_id,
            )
        )

        report = await ctx["reports"].get_by_id(report_id)
        assert report is not None
        assert report.generation_status == ShiftReportGenerationStatus.READY
        assert report.file_name is not None and report.file_name.endswith(".xlsx")
        assert report.storage_key is not None and report.storage_key.startswith("reports/")
        assert report.mime_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        assert len(ctx["snapshot"].calls) == 1
        assert len(ctx["renderer"].calls) == 1
        render_call = ctx["renderer"].calls[0]
        assert render_call["participants"][0]["username"] == "Ivan Ivanov"
        assert render_call["external_owner_sections"][0]["owner_display_name"] == "Owner"
        assert render_call["external_owner_sections"][0]["resources"][0]["title"] == "Sony A7"

    asyncio.run(scenario())


def test_process_shift_report_generation_uses_placeholders_for_missing_snapshot_fields() -> None:
    async def scenario() -> None:
        ctx = build_report_generation_context()
        now = now_utc()
        director_id = uuid4()
        participant_user_id = uuid4()
        project_id = uuid4()
        shift_id = uuid4()
        report_id = uuid4()
        resource_id = uuid4()

        await ctx["projects"].add(
            Project(
                oid=project_id,
                title="Feature film",
                description="Desc",
                owner_id=director_id,
                status=ProjectStatus.ACTIVE,
                created_at=now,
                updated_at=now,
            )
        )
        await ctx["shifts"].add(
            Shift(
                oid=shift_id,
                project_id=project_id,
                title="Night shoot",
                description="Desc",
                start_time=now,
                end_time=now + timedelta(hours=4),
                status=ShiftStatus.APPROVED,
                created_by=director_id,
                approved_by=director_id,
                approved_at=now,
                created_at=now,
                updated_at=now,
            )
        )
        await ctx["members"].add(
            ProjectMember(
                oid=uuid4(),
                project_id=project_id,
                user_id=director_id,
                role=ProjectRole.DIRECTOR,
                status=ProjectMemberStatus.ACTIVE,
                invited_by=director_id,
                created_at=now,
                updated_at=now,
            )
        )
        await ctx["members"].add(
            ProjectMember(
                oid=uuid4(),
                project_id=project_id,
                user_id=participant_user_id,
                role=ProjectRole.CAMERA,
                status=ProjectMemberStatus.ACTIVE,
                invited_by=director_id,
                created_at=now,
                updated_at=now,
            )
        )
        await ctx["participants"].add(
            ShiftParticipant(
                oid=uuid4(),
                shift_id=shift_id,
                user_id=participant_user_id,
                role=ProjectRole.CAMERA,
                time_from=now,
                time_to=now + timedelta(hours=2),
                status=ShiftParticipantStatus.CONFIRMED,
                added_by=director_id,
                created_at=now,
                updated_at=now,
            )
        )
        await ctx["requests"].add(
            ShiftResourceRequest(
                oid=uuid4(),
                project_id=project_id,
                shift_id=shift_id,
                resource_type="camera",
                resource_id=resource_id,
                resource_owner_user_id=participant_user_id,
                requested_by_user_id=director_id,
                time_from=now,
                time_to=now + timedelta(hours=2),
                status=ResourceRequestStatus.RESERVED,
                created_at=now,
                updated_at=now,
                resource_reservation_id=uuid4(),
            )
        )
        await ctx["reports"].add(
            ShiftReport(
                oid=report_id,
                project_id=project_id,
                shift_id=shift_id,
                version=1,
                generation_status=ShiftReportGenerationStatus.PENDING,
                actuality_status=ShiftReportActualityStatus.ACTUAL,
                requested_by_user_id=director_id,
                file_name=None,
                bucket=None,
                storage_key=None,
                mime_type=None,
                generated_at=None,
                archived_at=None,
                error_message=None,
                stale_reason=None,
                stale_marked_at=None,
                created_at=now,
                updated_at=now,
            )
        )

        await ctx["process_handler"](
            ProcessShiftReportGenerationCommand(
                report_id=report_id,
            )
        )

        render_call = ctx["renderer"].calls[0]
        assert render_call["participants"][0]["username"] == "Неизвестный пользователь"
        assert render_call["participants"][0]["phone"] == "Телефон не указан"
        assert render_call["owner_sections"][0]["resources"][0]["description"] == "Описание не указано"

    asyncio.run(scenario())


def test_process_shift_report_generation_marks_failed_after_snapshot_error() -> None:
    async def scenario() -> None:
        ctx = build_report_generation_context()
        now = now_utc()
        director_id = uuid4()
        project_id = uuid4()
        shift_id = uuid4()
        report_id = uuid4()

        await ctx["projects"].add(
            Project(
                oid=project_id,
                title="Feature film",
                description="Desc",
                owner_id=director_id,
                status=ProjectStatus.ACTIVE,
                created_at=now,
                updated_at=now,
            )
        )
        await ctx["shifts"].add(
            Shift(
                oid=shift_id,
                project_id=project_id,
                title="Night shoot",
                description="Desc",
                start_time=now,
                end_time=now + timedelta(hours=4),
                status=ShiftStatus.APPROVED,
                created_by=director_id,
                approved_by=director_id,
                approved_at=now,
                created_at=now,
                updated_at=now,
            )
        )
        await ctx["members"].add(
            ProjectMember(
                oid=uuid4(),
                project_id=project_id,
                user_id=director_id,
                role=ProjectRole.DIRECTOR,
                status=ProjectMemberStatus.ACTIVE,
                invited_by=director_id,
                created_at=now,
                updated_at=now,
            )
        )
        await ctx["reports"].add(
            ShiftReport(
                oid=report_id,
                project_id=project_id,
                shift_id=shift_id,
                version=1,
                generation_status=ShiftReportGenerationStatus.PENDING,
                actuality_status=ShiftReportActualityStatus.ACTUAL,
                requested_by_user_id=director_id,
                file_name=None,
                bucket=None,
                storage_key=None,
                mime_type=None,
                generated_at=None,
                archived_at=None,
                error_message=None,
                stale_reason=None,
                stale_marked_at=None,
                created_at=now,
                updated_at=now,
            )
        )
        ctx["snapshot"].fail = RuntimeError("broker failed")

        await ctx["process_handler"](
            ProcessShiftReportGenerationCommand(
                report_id=report_id,
            )
        )

        report = await ctx["reports"].get_by_id(report_id)
        assert report is not None
        assert report.generation_status == ShiftReportGenerationStatus.FAILED
        assert report.error_message is not None
        assert "broker failed" in report.error_message

    asyncio.run(scenario())


def test_archive_shift_report_sets_archived_status() -> None:
    async def scenario() -> None:
        ctx = build_report_generation_context()
        now = now_utc()
        director_id = uuid4()
        project_id = uuid4()
        shift_id = uuid4()
        report_id = uuid4()

        await ctx["shifts"].add(
            Shift(
                oid=shift_id,
                project_id=project_id,
                title="Approved shift",
                description="Desc",
                start_time=now,
                end_time=now + timedelta(hours=2),
                status=ShiftStatus.APPROVED,
                created_by=director_id,
                approved_by=director_id,
                approved_at=now,
                created_at=now,
                updated_at=now,
            )
        )
        await ctx["members"].add(
            ProjectMember(
                oid=uuid4(),
                project_id=project_id,
                user_id=director_id,
                role=ProjectRole.DIRECTOR,
                status=ProjectMemberStatus.ACTIVE,
                invited_by=director_id,
                created_at=now,
                updated_at=now,
            )
        )
        await ctx["reports"].add(
            ShiftReport(
                oid=report_id,
                project_id=project_id,
                shift_id=shift_id,
                version=1,
                generation_status=ShiftReportGenerationStatus.READY,
                actuality_status=ShiftReportActualityStatus.ACTUAL,
                requested_by_user_id=director_id,
                file_name="report.xlsx",
                bucket="bucket",
                storage_key="reports/report.xlsx",
                mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                generated_at=now,
                archived_at=None,
                error_message=None,
                stale_reason=None,
                stale_marked_at=None,
                created_at=now,
                updated_at=now,
            )
        )

        archived = await ctx["archive_handler"](
            ArchiveShiftReportCommand(
                report_id=report_id,
                actor_user_id=director_id,
            )
        )

        assert archived.generation_status == ShiftReportGenerationStatus.ARCHIVED
        assert archived.archived_at is not None

    asyncio.run(scenario())


def test_confirm_participant_marks_ready_reports_stale() -> None:
    async def scenario() -> None:
        tx = FakeTx()
        clock = SystemClock()
        publisher = FakePublisher()
        reservation_outbox = InMemoryReservationOutboxRepo()
        members = InMemoryProjectMemberRepo()
        shifts = InMemoryShiftRepo()
        participants = InMemoryParticipantRepo()
        reports = InMemoryShiftReportRepo()
        now = now_utc()
        director_id = uuid4()
        project_id = uuid4()
        shift_id = uuid4()
        participant_id = uuid4()
        user_id = uuid4()

        await shifts.add(
            Shift(
                oid=shift_id,
                project_id=project_id,
                title="Shift",
                description="Desc",
                start_time=now,
                end_time=now + timedelta(hours=2),
                status=ShiftStatus.DRAFT,
                created_by=director_id,
                created_at=now,
                updated_at=now,
            )
        )
        await participants.add(
            ShiftParticipant(
                oid=participant_id,
                shift_id=shift_id,
                user_id=user_id,
                role=ProjectRole.ACTOR,
                time_from=now,
                time_to=now + timedelta(hours=1),
                status=ShiftParticipantStatus.INVITED,
                added_by=director_id,
                created_at=now,
                updated_at=now,
            )
        )
        await members.add(
            ProjectMember(
                oid=uuid4(),
                project_id=project_id,
                user_id=user_id,
                role=ProjectRole.ACTOR,
                status=ProjectMemberStatus.ACTIVE,
                invited_by=director_id,
                created_at=now,
                updated_at=now,
            )
        )
        await reports.add(
            ShiftReport(
                oid=uuid4(),
                project_id=project_id,
                shift_id=shift_id,
                version=1,
                generation_status=ShiftReportGenerationStatus.READY,
                actuality_status=ShiftReportActualityStatus.ACTUAL,
                requested_by_user_id=director_id,
                file_name="report.xlsx",
                bucket="bucket",
                storage_key="reports/report.xlsx",
                mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                generated_at=now,
                archived_at=None,
                error_message=None,
                stale_reason=None,
                stale_marked_at=None,
                created_at=now,
                updated_at=now,
            )
        )
        handler = ConfirmShiftParticipantHandler(
            transaction_manager=tx,
            clock=clock,
            publisher=publisher,
            reservation_outbox=reservation_outbox,
            project_members=members,
            shifts=shifts,
            shift_participants=participants,
            shift_reports=reports,
            shift_participant_service=ShiftParticipantService(),
        )

        await handler(
            ConfirmShiftParticipantCommand(
                participant_id=participant_id,
                actor_user_id=user_id,
            )
        )

        report = (await reports.list_by_shift(shift_id))[0]
        assert report.actuality_status == ShiftReportActualityStatus.STALE
        assert report.stale_reason == "Participant status changed."

    asyncio.run(scenario())


def test_create_resource_request_marks_ready_reports_stale() -> None:
    async def scenario() -> None:
        tx = FakeTx()
        clock = SystemClock()
        publisher = FakePublisher()
        project_members = InMemoryProjectMemberRepo()
        shifts = InMemoryShiftRepo()
        requests = InMemoryResourceRequestRepo()
        reports = InMemoryShiftReportRepo()
        now = now_utc()
        director_id = uuid4()
        project_id = uuid4()
        shift_id = uuid4()

        await shifts.add(
            Shift(
                oid=shift_id,
                project_id=project_id,
                title="Shift",
                description="Desc",
                start_time=now,
                end_time=now + timedelta(hours=2),
                status=ShiftStatus.DRAFT,
                created_by=director_id,
                created_at=now,
                updated_at=now,
            )
        )
        await project_members.add(
            ProjectMember(
                oid=uuid4(),
                project_id=project_id,
                user_id=director_id,
                role=ProjectRole.DIRECTOR,
                status=ProjectMemberStatus.ACTIVE,
                invited_by=director_id,
                created_at=now,
                updated_at=now,
            )
        )
        resource_owner_user_id = uuid4()
        resource_id = uuid4()
        await project_members.add(
            ProjectMember(
                oid=uuid4(),
                project_id=project_id,
                user_id=resource_owner_user_id,
                role=ProjectRole.CAMERA,
                status=ProjectMemberStatus.ACTIVE,
                invited_by=director_id,
                created_at=now,
                updated_at=now,
            )
        )
        user_service = FakeUserService()
        user_service.resources[(resource_owner_user_id, "cameras")] = [
            UserResourceItem(
                resource_kind="cameras",
                resource_id=resource_id,
                title="Sony",
                description="Camera",
                resource_type="mirrorless",
                size=None,
                created_at=now,
                windows=(),
            )
        ]
        await reports.add(
            ShiftReport(
                oid=uuid4(),
                project_id=project_id,
                shift_id=shift_id,
                version=1,
                generation_status=ShiftReportGenerationStatus.READY,
                actuality_status=ShiftReportActualityStatus.ACTUAL,
                requested_by_user_id=director_id,
                file_name="report.xlsx",
                bucket="bucket",
                storage_key="reports/report.xlsx",
                mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                generated_at=now,
                archived_at=None,
                error_message=None,
                stale_reason=None,
                stale_marked_at=None,
                created_at=now,
                updated_at=now,
            )
        )
        handler = CreateResourceRequestHandler(
            transaction_manager=tx,
            clock=clock,
            id_generator=FakeIdGenerator(),
            publisher=publisher,
            user_service=user_service,
            project_members=project_members,
            shifts=shifts,
            resource_requests=requests,
            shift_reports=reports,
            resource_request_service=ResourceRequestService(),
        )

        await handler(
            CreateResourceRequestCommand(
                shift_id=shift_id,
                actor_user_id=director_id,
                resource_type="camera",
                resource_id=resource_id,
                resource_owner_user_id=resource_owner_user_id,
                time_from=now,
                time_to=now + timedelta(hours=1),
            )
        )

        report = (await reports.list_by_shift(shift_id))[0]
        assert report.actuality_status == ShiftReportActualityStatus.STALE
        assert report.stale_reason == "Resource request composition changed."

    asyncio.run(scenario())


def test_create_resource_request_requires_owner_active_project_member() -> None:
    async def scenario() -> None:
        tx = FakeTx()
        clock = SystemClock()
        publisher = FakePublisher()
        user_service = FakeUserService()
        project_members = InMemoryProjectMemberRepo()
        shifts = InMemoryShiftRepo()
        requests = InMemoryResourceRequestRepo()
        reports = InMemoryShiftReportRepo()
        now = now_utc()
        director_id = uuid4()
        external_owner_id = uuid4()
        project_id = uuid4()
        shift_id = uuid4()
        resource_id = uuid4()

        await shifts.add(
            Shift(
                oid=shift_id,
                project_id=project_id,
                title="Shift",
                description="Desc",
                start_time=now,
                end_time=now + timedelta(hours=2),
                status=ShiftStatus.DRAFT,
                created_by=director_id,
                created_at=now,
                updated_at=now,
            )
        )
        await project_members.add(
            ProjectMember(
                oid=uuid4(),
                project_id=project_id,
                user_id=director_id,
                role=ProjectRole.DIRECTOR,
                status=ProjectMemberStatus.ACTIVE,
                invited_by=director_id,
                created_at=now,
                updated_at=now,
            )
        )
        user_service.resources[(external_owner_id, "cameras")] = [
            UserResourceItem(
                resource_kind="cameras",
                resource_id=resource_id,
                title="External camera",
                description="Not in project",
                resource_type="mirrorless",
                size=None,
                created_at=now,
                windows=(),
            )
        ]
        handler = CreateResourceRequestHandler(
            transaction_manager=tx,
            clock=clock,
            id_generator=FakeIdGenerator(),
            publisher=publisher,
            user_service=user_service,
            project_members=project_members,
            shifts=shifts,
            resource_requests=requests,
            shift_reports=reports,
            resource_request_service=ResourceRequestService(),
        )

        with pytest.raises(EntityNotFoundError):
            await handler(
                CreateResourceRequestCommand(
                    shift_id=shift_id,
                    actor_user_id=director_id,
                    resource_type="camera",
                    resource_id=resource_id,
                    resource_owner_user_id=external_owner_id,
                    time_from=now,
                    time_to=now + timedelta(hours=1),
                )
            )

        assert requests.data == {}
        assert tx.rollbacks == 1

    asyncio.run(scenario())


def test_create_resource_request_requires_resource_owned_by_member() -> None:
    async def scenario() -> None:
        tx = FakeTx()
        clock = SystemClock()
        publisher = FakePublisher()
        user_service = FakeUserService()
        project_members = InMemoryProjectMemberRepo()
        shifts = InMemoryShiftRepo()
        requests = InMemoryResourceRequestRepo()
        reports = InMemoryShiftReportRepo()
        now = now_utc()
        director_id = uuid4()
        owner_id = uuid4()
        project_id = uuid4()
        shift_id = uuid4()

        await shifts.add(
            Shift(
                oid=shift_id,
                project_id=project_id,
                title="Shift",
                description="Desc",
                start_time=now,
                end_time=now + timedelta(hours=2),
                status=ShiftStatus.DRAFT,
                created_by=director_id,
                created_at=now,
                updated_at=now,
            )
        )
        for user_id, role in ((director_id, ProjectRole.DIRECTOR), (owner_id, ProjectRole.CAMERA)):
            await project_members.add(
                ProjectMember(
                    oid=uuid4(),
                    project_id=project_id,
                    user_id=user_id,
                    role=role,
                    status=ProjectMemberStatus.ACTIVE,
                    invited_by=director_id,
                    created_at=now,
                    updated_at=now,
                )
            )
        handler = CreateResourceRequestHandler(
            transaction_manager=tx,
            clock=clock,
            id_generator=FakeIdGenerator(),
            publisher=publisher,
            user_service=user_service,
            project_members=project_members,
            shifts=shifts,
            resource_requests=requests,
            shift_reports=reports,
            resource_request_service=ResourceRequestService(),
        )

        with pytest.raises(EntityNotFoundError):
            await handler(
                CreateResourceRequestCommand(
                    shift_id=shift_id,
                    actor_user_id=director_id,
                    resource_type="camera",
                    resource_id=uuid4(),
                    resource_owner_user_id=owner_id,
                    time_from=now,
                    time_to=now + timedelta(hours=1),
                )
            )

        assert requests.data == {}
        assert tx.rollbacks == 1

    asyncio.run(scenario())


def test_create_resource_request_uses_actor_role_resource_kinds() -> None:
    async def scenario() -> None:
        tx = FakeTx()
        clock = SystemClock()
        publisher = FakePublisher()
        user_service = FakeUserService()
        project_members = InMemoryProjectMemberRepo()
        shifts = InMemoryShiftRepo()
        requests = InMemoryResourceRequestRepo()
        reports = InMemoryShiftReportRepo()
        now = now_utc()
        actor_id = uuid4()
        owner_id = uuid4()
        project_id = uuid4()
        shift_id = uuid4()

        await shifts.add(
            Shift(
                oid=shift_id,
                project_id=project_id,
                title="Shift",
                description="Desc",
                start_time=now,
                end_time=now + timedelta(hours=2),
                status=ShiftStatus.DRAFT,
                created_by=actor_id,
                created_at=now,
                updated_at=now,
            )
        )
        for user_id, role in ((actor_id, ProjectRole.CAMERA), (owner_id, ProjectRole.LIGHT)):
            await project_members.add(
                ProjectMember(
                    oid=uuid4(),
                    project_id=project_id,
                    user_id=user_id,
                    role=role,
                    status=ProjectMemberStatus.ACTIVE,
                    invited_by=actor_id,
                    created_at=now,
                    updated_at=now,
                )
            )
        handler = CreateResourceRequestHandler(
            transaction_manager=tx,
            clock=clock,
            id_generator=FakeIdGenerator(),
            publisher=publisher,
            user_service=user_service,
            project_members=project_members,
            shifts=shifts,
            resource_requests=requests,
            shift_reports=reports,
            resource_request_service=ResourceRequestService(),
        )

        with pytest.raises(AccessDeniedError):
            await handler(
                CreateResourceRequestCommand(
                    shift_id=shift_id,
                    actor_user_id=actor_id,
                    resource_type="light",
                    resource_id=uuid4(),
                    resource_owner_user_id=owner_id,
                    time_from=now,
                    time_to=now + timedelta(hours=1),
                )
            )

        assert requests.data == {}
        assert tx.rollbacks == 1

    asyncio.run(scenario())


def _build_shift_reminder_context():
    tx = FakeTx()
    publisher = FakePublisher()
    clock = SystemClock()
    projects = InMemoryProjectRepo()
    members = InMemoryProjectMemberRepo()
    shifts = InMemoryShiftRepo()
    participants = InMemoryParticipantRepo()
    requests = InMemoryResourceRequestRepo()
    reservation_outbox = InMemoryReservationOutboxRepo()
    reports = InMemoryShiftReportRepo()
    reminders = InMemoryShiftReminderRepo()
    report_tasks = FakeShiftReportTaskDispatcher()
    settings = ShiftReminderSettings()
    approve_handler = ApproveShiftHandler(
        transaction_manager=tx,
        clock=clock,
        id_generator=FakeIdGenerator(),
        publisher=publisher,
        project_members=members,
        shifts=shifts,
        shift_participants=participants,
        resource_requests=requests,
        reservation_outbox=reservation_outbox,
        shift_reports=reports,
        shift_reminders=reminders,
        report_task_dispatcher=report_tasks,
        shift_service=ShiftService(),
        shift_participant_service=ShiftParticipantService(),
        resource_request_service=ResourceRequestService(),
        shift_reminder_settings=settings,
    )
    cancel_handler = CancelShiftHandler(
        transaction_manager=tx,
        clock=clock,
        publisher=publisher,
        reservation_outbox=reservation_outbox,
        project_members=members,
        shifts=shifts,
        shift_participants=participants,
        resource_requests=requests,
        shift_reports=reports,
        shift_reminders=reminders,
        shift_service=ShiftService(),
        shift_participant_service=ShiftParticipantService(),
        resource_request_service=ResourceRequestService(),
    )
    process_handler = ProcessShiftRemindersHandler(
        transaction_manager=tx,
        clock=clock,
        publisher=publisher,
        projects=projects,
        shifts=shifts,
        shift_participants=participants,
        resource_requests=requests,
        shift_reminders=reminders,
    )
    return (
        tx,
        publisher,
        projects,
        members,
        shifts,
        participants,
        requests,
        reminders,
        settings,
        approve_handler,
        cancel_handler,
        process_handler,
    )


def _seed_director(members: InMemoryProjectMemberRepo, *, project_id: UUID, now: datetime) -> UUID:
    director_id = uuid4()
    members.data[(project_id, director_id)] = ProjectMember(
        oid=uuid4(),
        project_id=project_id,
        user_id=director_id,
        role=ProjectRole.DIRECTOR,
        status=ProjectMemberStatus.ACTIVE,
        invited_by=director_id,
        created_at=now,
        updated_at=now,
    )
    return director_id


def test_approve_shift_creates_pending_reminder_one_offset_before_start() -> None:
    async def scenario():
        (
            _tx,
            _publisher,
            projects,
            members,
            shifts,
            _participants,
            _requests,
            reminders,
            settings,
            approve_handler,
            _cancel_handler,
            _process_handler,
        ) = _build_shift_reminder_context()
        now = now_utc()
        project_id = uuid4()
        director_id = _seed_director(members, project_id=project_id, now=now)
        await projects.add(
            Project(
                title="P",
                description="",
                owner_id=director_id,
                status=ProjectStatus.ACTIVE,
                oid=project_id,
                created_at=now,
                updated_at=now,
            )
        )
        start_time = now + timedelta(days=1)
        shift = Shift(
            oid=uuid4(),
            project_id=project_id,
            title="S",
            description="D",
            start_time=start_time,
            end_time=start_time + timedelta(hours=3),
            status=ShiftStatus.DRAFT,
            created_by=director_id,
            created_at=now,
            updated_at=now,
        )
        shifts.data[shift.oid] = shift

        await approve_handler(
            ApproveShiftCommand(shift_id=shift.oid, actor_user_id=director_id)
        )

        reminder = await reminders.get_by_shift(shift.oid)
        assert reminder is not None
        assert reminder.status == ShiftReminderStatus.PENDING
        assert reminder.fire_at == start_time - timedelta(seconds=settings.offset_seconds)

        # Re-approving reuses the same reminder row instead of duplicating it.
        shift.status = ShiftStatus.DRAFT
        await approve_handler(
            ApproveShiftCommand(shift_id=shift.oid, actor_user_id=director_id)
        )
        assert len(reminders.data) == 1

    asyncio.run(scenario())


def test_process_shift_reminders_dispatches_eligible_participants_with_resources() -> None:
    async def scenario():
        (
            _tx,
            publisher,
            projects,
            members,
            shifts,
            participants,
            requests,
            reminders,
            _settings,
            approve_handler,
            _cancel_handler,
            process_handler,
        ) = _build_shift_reminder_context()
        now = now_utc()
        project_id = uuid4()
        director_id = _seed_director(members, project_id=project_id, now=now)
        await projects.add(
            Project(
                title="Movie",
                description="",
                owner_id=director_id,
                status=ProjectStatus.ACTIVE,
                oid=project_id,
                created_at=now,
                updated_at=now,
            )
        )
        start_time = now + timedelta(minutes=30)
        shift = Shift(
            oid=uuid4(),
            project_id=project_id,
            title="Night shoot",
            description="D",
            start_time=start_time,
            end_time=start_time + timedelta(hours=3),
            status=ShiftStatus.DRAFT,
            created_by=director_id,
            created_at=now,
            updated_at=now,
        )
        shifts.data[shift.oid] = shift

        confirmed_user = uuid4()
        declined_user = uuid4()
        confirmed_participant = ShiftParticipant(
            oid=uuid4(),
            shift_id=shift.oid,
            user_id=confirmed_user,
            role=ProjectRole.CAMERA,
            time_from=start_time,
            time_to=start_time + timedelta(hours=2),
            status=ShiftParticipantStatus.RESERVED,
            added_by=director_id,
            created_at=now,
            updated_at=now,
        )
        declined_participant = ShiftParticipant(
            oid=uuid4(),
            shift_id=shift.oid,
            user_id=declined_user,
            role=ProjectRole.SOUND,
            time_from=start_time,
            time_to=start_time + timedelta(hours=2),
            status=ShiftParticipantStatus.DECLINED,
            added_by=director_id,
            created_at=now,
            updated_at=now,
        )
        await participants.add(confirmed_participant)
        await participants.add(declined_participant)

        await requests.add(
            ShiftResourceRequest(
                oid=uuid4(),
                project_id=project_id,
                shift_id=shift.oid,
                resource_type="cameras",
                resource_id=uuid4(),
                resource_owner_user_id=confirmed_user,
                requested_by_user_id=director_id,
                time_from=start_time,
                time_to=start_time + timedelta(hours=1),
                status=ResourceRequestStatus.RESERVED,
                created_at=now,
                updated_at=now,
            )
        )
        # Cancelled request must be ignored.
        await requests.add(
            ShiftResourceRequest(
                oid=uuid4(),
                project_id=project_id,
                shift_id=shift.oid,
                resource_type="lights",
                resource_id=uuid4(),
                resource_owner_user_id=confirmed_user,
                requested_by_user_id=director_id,
                time_from=start_time,
                time_to=start_time + timedelta(hours=1),
                status=ResourceRequestStatus.CANCELLED,
                created_at=now,
                updated_at=now,
            )
        )

        await approve_handler(
            ApproveShiftCommand(shift_id=shift.oid, actor_user_id=director_id)
        )
        reminder = await reminders.get_by_shift(shift.oid)
        assert reminder is not None
        # fire_at is already in the past (shift starts within the offset window).
        assert reminder.fire_at <= now_utc()

        processed = await process_handler(limit=10)

        assert processed == 1
        reminder = await reminders.get_by_shift(shift.oid)
        assert reminder.status == ShiftReminderStatus.SENT

        reminder_events = [
            payload
            for topic, payload in publisher.events
            if topic == SHIFT_REMINDER_REQUESTED_TOPIC
        ]
        assert len(reminder_events) == 1
        event = reminder_events[0]
        assert event["user_id"] == str(confirmed_user)
        assert event["shift_title"] == "Night shoot"
        assert event["project_title"] == "Movie"
        assert event["role"] == "CAMERA"
        assert event["notification_id"] == str(
            build_reminder_notification_id(
                reminder_id=reminder.oid,
                participant_id=confirmed_participant.oid,
            )
        )
        assert [res["resource_type"] for res in event["resources"]] == ["cameras"]

        # Already SENT: a second poll dispatches nothing.
        assert await process_handler(limit=10) == 0

    asyncio.run(scenario())


def test_process_shift_reminders_cancels_when_shift_not_approved() -> None:
    async def scenario():
        (
            _tx,
            publisher,
            _projects,
            members,
            shifts,
            _participants,
            _requests,
            reminders,
            _settings,
            _approve_handler,
            _cancel_handler,
            process_handler,
        ) = _build_shift_reminder_context()
        now = now_utc()
        project_id = uuid4()
        director_id = _seed_director(members, project_id=project_id, now=now)
        shift = Shift(
            oid=uuid4(),
            project_id=project_id,
            title="S",
            description="D",
            start_time=now + timedelta(minutes=10),
            end_time=now + timedelta(hours=3),
            status=ShiftStatus.CANCELLED,
            created_by=director_id,
            created_at=now,
            updated_at=now,
        )
        shifts.data[shift.oid] = shift
        await reminders.add(
            ShiftReminder(
                oid=uuid4(),
                shift_id=shift.oid,
                fire_at=now - timedelta(minutes=1),
                status=ShiftReminderStatus.PENDING,
                created_at=now,
                updated_at=now,
            )
        )

        processed = await process_handler(limit=10)

        assert processed == 1
        reminder = await reminders.get_by_shift(shift.oid)
        assert reminder.status == ShiftReminderStatus.CANCELLED
        assert publisher.events == []

    asyncio.run(scenario())


def test_cancel_shift_cancels_pending_reminder() -> None:
    async def scenario():
        (
            _tx,
            _publisher,
            projects,
            members,
            shifts,
            _participants,
            _requests,
            reminders,
            _settings,
            approve_handler,
            cancel_handler,
            _process_handler,
        ) = _build_shift_reminder_context()
        now = now_utc()
        project_id = uuid4()
        director_id = _seed_director(members, project_id=project_id, now=now)
        await projects.add(
            Project(
                title="P",
                description="",
                owner_id=director_id,
                status=ProjectStatus.ACTIVE,
                oid=project_id,
                created_at=now,
                updated_at=now,
            )
        )
        start_time = now + timedelta(days=1)
        shift = Shift(
            oid=uuid4(),
            project_id=project_id,
            title="S",
            description="D",
            start_time=start_time,
            end_time=start_time + timedelta(hours=3),
            status=ShiftStatus.DRAFT,
            created_by=director_id,
            created_at=now,
            updated_at=now,
        )
        shifts.data[shift.oid] = shift

        await approve_handler(
            ApproveShiftCommand(shift_id=shift.oid, actor_user_id=director_id)
        )
        await cancel_handler(
            CancelShiftCommand(shift_id=shift.oid, actor_user_id=director_id)
        )

        reminder = await reminders.get_by_shift(shift.oid)
        assert reminder is not None
        assert reminder.status == ShiftReminderStatus.CANCELLED

    asyncio.run(scenario())


def test_process_shift_reminders_accepts_plain_int_statuses_from_orm() -> None:
    # The ORM maps status/role columns as plain integers, so the worker must
    # tolerate raw ints (not only enum members) when filtering and rendering.
    async def scenario():
        (
            _tx,
            publisher,
            projects,
            members,
            shifts,
            participants,
            requests,
            reminders,
            _settings,
            _approve_handler,
            _cancel_handler,
            process_handler,
        ) = _build_shift_reminder_context()
        now = now_utc()
        project_id = uuid4()
        director_id = _seed_director(members, project_id=project_id, now=now)
        await projects.add(
            Project(
                title="Movie",
                description="",
                owner_id=director_id,
                status=int(ProjectStatus.ACTIVE),
                oid=project_id,
                created_at=now,
                updated_at=now,
            )
        )
        start_time = now + timedelta(minutes=30)
        shift = Shift(
            oid=uuid4(),
            project_id=project_id,
            title="Night shoot",
            description="D",
            start_time=start_time,
            end_time=start_time + timedelta(hours=3),
            status=int(ShiftStatus.APPROVED),
            created_by=director_id,
            created_at=now,
            updated_at=now,
        )
        shifts.data[shift.oid] = shift

        member_user = uuid4()
        participant = ShiftParticipant(
            oid=uuid4(),
            shift_id=shift.oid,
            user_id=member_user,
            role=int(ProjectRole.CAMERA),
            time_from=start_time,
            time_to=start_time + timedelta(hours=2),
            status=int(ShiftParticipantStatus.RESERVED),
            added_by=director_id,
            created_at=now,
            updated_at=now,
        )
        await participants.add(participant)
        await requests.add(
            ShiftResourceRequest(
                oid=uuid4(),
                project_id=project_id,
                shift_id=shift.oid,
                resource_type="cameras",
                resource_id=uuid4(),
                resource_owner_user_id=member_user,
                requested_by_user_id=director_id,
                time_from=start_time,
                time_to=start_time + timedelta(hours=1),
                status=int(ResourceRequestStatus.RESERVED),
                created_at=now,
                updated_at=now,
            )
        )
        await reminders.add(
            ShiftReminder(
                oid=uuid4(),
                shift_id=shift.oid,
                fire_at=now - timedelta(minutes=1),
                status=int(ShiftReminderStatus.PENDING),
                created_at=now,
                updated_at=now,
            )
        )

        processed = await process_handler(limit=10)

        assert processed == 1
        events = [
            payload
            for topic, payload in publisher.events
            if topic == SHIFT_REMINDER_REQUESTED_TOPIC
        ]
        assert len(events) == 1
        assert events[0]["role"] == "CAMERA"
        assert [res["resource_type"] for res in events[0]["resources"]] == ["cameras"]

    asyncio.run(scenario())


def _build_approval_context() -> SimpleNamespace:
    tx = FakeTx()
    publisher = FakePublisher()
    user_service = FakeUserService()
    clock = SystemClock()
    projects = InMemoryProjectRepo()
    members = InMemoryProjectMemberRepo()
    shifts = InMemoryShiftRepo()
    participants = InMemoryParticipantRepo()
    requests = InMemoryResourceRequestRepo()
    reservation_outbox = InMemoryReservationOutboxRepo()
    reports = InMemoryShiftReportRepo()
    reminders = InMemoryShiftReminderRepo()
    report_tasks = FakeShiftReportTaskDispatcher()
    approve = ApproveShiftHandler(
        transaction_manager=tx,
        clock=clock,
        id_generator=FakeIdGenerator(),
        publisher=publisher,
        project_members=members,
        shifts=shifts,
        shift_participants=participants,
        resource_requests=requests,
        reservation_outbox=reservation_outbox,
        shift_reports=reports,
        shift_reminders=reminders,
        report_task_dispatcher=report_tasks,
        shift_service=ShiftService(),
        shift_participant_service=ShiftParticipantService(),
        resource_request_service=ResourceRequestService(),
        shift_reminder_settings=ShiftReminderSettings(),
    )
    confirm = ConfirmShiftParticipantHandler(
        transaction_manager=tx,
        clock=clock,
        publisher=publisher,
        reservation_outbox=reservation_outbox,
        project_members=members,
        shifts=shifts,
        shift_participants=participants,
        shift_reports=reports,
        shift_participant_service=ShiftParticipantService(),
    )
    invite = InviteShiftParticipantHandler(
        transaction_manager=tx,
        clock=clock,
        id_generator=FakeIdGenerator(),
        publisher=publisher,
        user_service=user_service,
        project_members=members,
        shifts=shifts,
        shift_participants=participants,
        shift_reports=reports,
        shift_participant_service=ShiftParticipantService(),
    )
    return SimpleNamespace(
        tx=tx,
        publisher=publisher,
        user_service=user_service,
        projects=projects,
        members=members,
        shifts=shifts,
        participants=participants,
        requests=requests,
        reservation_outbox=reservation_outbox,
        reports=reports,
        reminders=reminders,
        report_tasks=report_tasks,
        approve=approve,
        confirm=confirm,
        invite=invite,
    )


async def _seed_project_and_member(
    ctx: SimpleNamespace,
    *,
    user_id: UUID,
    role: ProjectRole,
    now: datetime,
    project_id: UUID | None = None,
) -> UUID:
    project_id = project_id or uuid4()
    if project_id not in ctx.projects.data:
        await ctx.projects.add(
            Project(
                title="P",
                description="",
                owner_id=user_id,
                status=ProjectStatus.ACTIVE,
                oid=project_id,
                created_at=now,
                updated_at=now,
            )
        )
    ctx.members.data[(project_id, user_id)] = ProjectMember(
        oid=uuid4(),
        project_id=project_id,
        user_id=user_id,
        role=role,
        status=ProjectMemberStatus.ACTIVE,
        invited_by=user_id,
        created_at=now,
        updated_at=now,
    )
    return project_id


def _make_shift(*, project_id: UUID, director_id: UUID, start: datetime, hours: int) -> Shift:
    return Shift(
        oid=uuid4(),
        project_id=project_id,
        title="S",
        description="D",
        start_time=start,
        end_time=start + timedelta(hours=hours),
        status=ShiftStatus.DRAFT,
        created_by=director_id,
        created_at=start,
        updated_at=start,
    )


def _make_participant(
    *,
    shift: Shift,
    user_id: UUID,
    status: ShiftParticipantStatus,
    director_id: UUID,
    now: datetime,
    reservation_id: UUID | None = None,
) -> ShiftParticipant:
    return ShiftParticipant(
        oid=uuid4(),
        shift_id=shift.oid,
        user_id=user_id,
        role=ProjectRole.CAMERA,
        time_from=shift.start_time,
        time_to=shift.start_time + timedelta(hours=1),
        status=status,
        added_by=director_id,
        created_at=now,
        updated_at=now,
        user_reservation_id=reservation_id,
    )


def test_approve_shift_keeps_only_reserved_participants_and_resources() -> None:
    async def scenario():
        ctx = _build_approval_context()
        now = now_utc()
        director_id = uuid4()
        project_id = await _seed_project_and_member(
            ctx, user_id=director_id, role=ProjectRole.DIRECTOR, now=now
        )
        start = now + timedelta(days=1)
        shift = _make_shift(project_id=project_id, director_id=director_id, start=start, hours=4)
        await ctx.shifts.add(shift)

        reserved = _make_participant(
            shift=shift,
            user_id=uuid4(),
            status=ShiftParticipantStatus.RESERVED,
            director_id=director_id,
            now=now,
            reservation_id=uuid4(),
        )
        invited = _make_participant(
            shift=shift,
            user_id=uuid4(),
            status=ShiftParticipantStatus.INVITED,
            director_id=director_id,
            now=now,
        )
        reserving = _make_participant(
            shift=shift,
            user_id=uuid4(),
            status=ShiftParticipantStatus.RESERVING,
            director_id=director_id,
            now=now,
        )
        for participant in (reserved, invited, reserving):
            await ctx.participants.add(participant)

        def _make_request(status: ResourceRequestStatus, reservation_id=None):
            return ShiftResourceRequest(
                oid=uuid4(),
                project_id=project_id,
                shift_id=shift.oid,
                resource_type="cameras",
                resource_id=uuid4(),
                resource_owner_user_id=uuid4(),
                requested_by_user_id=director_id,
                time_from=start,
                time_to=start + timedelta(hours=1),
                status=status,
                created_at=now,
                updated_at=now,
                resource_reservation_id=reservation_id,
            )

        reserved_req = _make_request(ResourceRequestStatus.RESERVED, uuid4())
        pending_req = _make_request(ResourceRequestStatus.PENDING_OWNER)
        approved_req = _make_request(ResourceRequestStatus.APPROVED_OWNER)
        for request in (reserved_req, pending_req, approved_req):
            await ctx.requests.add(request)

        await ctx.approve(ApproveShiftCommand(shift_id=shift.oid, actor_user_id=director_id))

        assert ctx.participants.by_id[reserved.oid].status == ShiftParticipantStatus.RESERVED
        assert ctx.participants.by_id[invited.oid].status == ShiftParticipantStatus.CANCELLED
        assert ctx.participants.by_id[reserving.oid].status == ShiftParticipantStatus.CANCELLED

        assert ctx.requests.data[reserved_req.oid].status == ResourceRequestStatus.RESERVED
        assert ctx.requests.data[pending_req.oid].status == ResourceRequestStatus.CANCELLED
        assert ctx.requests.data[approved_req.oid].status == ResourceRequestStatus.CANCELLED

        # The RESERVED participant had a reservation, so a cancel must NOT be enqueued
        # (it stays on the shift); cancelled ones had no reservation -> no dispatch.
        assert ctx.reservation_outbox.data == {}

    asyncio.run(scenario())


def test_approve_shift_creates_and_schedules_report() -> None:
    async def scenario():
        ctx = _build_approval_context()
        now = now_utc()
        director_id = uuid4()
        project_id = await _seed_project_and_member(
            ctx, user_id=director_id, role=ProjectRole.DIRECTOR, now=now
        )
        start = now + timedelta(days=1)
        shift = _make_shift(project_id=project_id, director_id=director_id, start=start, hours=4)
        await ctx.shifts.add(shift)

        await ctx.approve(ApproveShiftCommand(shift_id=shift.oid, actor_user_id=director_id))

        reports = list(ctx.reports.data.values())
        assert len(reports) == 1
        report = reports[0]
        assert report.version == 1
        assert report.generation_status == ShiftReportGenerationStatus.PENDING
        assert report.requested_by_user_id == director_id
        assert len(ctx.report_tasks.commands) == 1
        assert ctx.report_tasks.commands[0].report_id == report.oid

    asyncio.run(scenario())


def test_confirm_blocked_by_overlapping_active_participation() -> None:
    async def scenario():
        ctx = _build_approval_context()
        now = now_utc()
        director_id = uuid4()
        user_id = uuid4()
        project_id = await _seed_project_and_member(
            ctx, user_id=director_id, role=ProjectRole.DIRECTOR, now=now
        )
        await _seed_project_and_member(
            ctx, user_id=user_id, role=ProjectRole.CAMERA, now=now, project_id=project_id
        )
        start = now + timedelta(days=1)
        shift_a = _make_shift(project_id=project_id, director_id=director_id, start=start, hours=4)
        shift_b = _make_shift(project_id=project_id, director_id=director_id, start=start, hours=4)
        await ctx.shifts.add(shift_a)
        await ctx.shifts.add(shift_b)

        # Same user invited to two overlapping shifts (allowed).
        participant_a = _make_participant(
            shift=shift_a,
            user_id=user_id,
            status=ShiftParticipantStatus.INVITED,
            director_id=director_id,
            now=now,
        )
        participant_b = _make_participant(
            shift=shift_b,
            user_id=user_id,
            status=ShiftParticipantStatus.INVITED,
            director_id=director_id,
            now=now,
        )
        await ctx.participants.add(participant_a)
        await ctx.participants.add(participant_b)

        await ctx.confirm(
            ConfirmShiftParticipantCommand(
                participant_id=participant_a.oid, actor_user_id=user_id
            )
        )
        # Now confirming the overlapping invitation is rejected.
        with pytest.raises(StateTransitionError):
            await ctx.confirm(
                ConfirmShiftParticipantCommand(
                    participant_id=participant_b.oid, actor_user_id=user_id
                )
            )
        assert ctx.participants.by_id[participant_b.oid].status == ShiftParticipantStatus.INVITED

    asyncio.run(scenario())


def test_confirm_allowed_for_non_overlapping_shifts() -> None:
    async def scenario():
        ctx = _build_approval_context()
        now = now_utc()
        director_id = uuid4()
        user_id = uuid4()
        project_id = await _seed_project_and_member(
            ctx, user_id=director_id, role=ProjectRole.DIRECTOR, now=now
        )
        await _seed_project_and_member(
            ctx, user_id=user_id, role=ProjectRole.CAMERA, now=now, project_id=project_id
        )
        start = now + timedelta(days=1)
        shift_a = _make_shift(project_id=project_id, director_id=director_id, start=start, hours=2)
        shift_b = _make_shift(
            project_id=project_id,
            director_id=director_id,
            start=start + timedelta(hours=5),
            hours=2,
        )
        await ctx.shifts.add(shift_a)
        await ctx.shifts.add(shift_b)

        participant_a = _make_participant(
            shift=shift_a,
            user_id=user_id,
            status=ShiftParticipantStatus.INVITED,
            director_id=director_id,
            now=now,
        )
        participant_b = _make_participant(
            shift=shift_b,
            user_id=user_id,
            status=ShiftParticipantStatus.INVITED,
            director_id=director_id,
            now=now,
        )
        await ctx.participants.add(participant_a)
        await ctx.participants.add(participant_b)

        await ctx.confirm(
            ConfirmShiftParticipantCommand(
                participant_id=participant_a.oid, actor_user_id=user_id
            )
        )
        await ctx.confirm(
            ConfirmShiftParticipantCommand(
                participant_id=participant_b.oid, actor_user_id=user_id
            )
        )
        assert ctx.participants.by_id[participant_a.oid].status == ShiftParticipantStatus.RESERVING
        assert ctx.participants.by_id[participant_b.oid].status == ShiftParticipantStatus.RESERVING

    asyncio.run(scenario())


def test_invite_participant_rejected_for_non_project_member() -> None:
    async def scenario():
        ctx = _build_approval_context()
        now = now_utc()
        director_id = uuid4()
        outsider_id = uuid4()
        project_id = await _seed_project_and_member(
            ctx, user_id=director_id, role=ProjectRole.DIRECTOR, now=now
        )
        start = now + timedelta(days=1)
        shift = _make_shift(project_id=project_id, director_id=director_id, start=start, hours=4)
        await ctx.shifts.add(shift)

        with pytest.raises(EntityNotFoundError):
            await ctx.invite(
                InviteShiftParticipantCommand(
                    shift_id=shift.oid,
                    actor_user_id=director_id,
                    participant_user_id=outsider_id,
                    role=ProjectRole.CAMERA,
                    time_from=start,
                    time_to=start + timedelta(hours=1),
                )
            )
        assert ctx.participants.by_id == {}

    asyncio.run(scenario())
