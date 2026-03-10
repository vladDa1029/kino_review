import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.application.commands.participants import (
    ConfirmShiftParticipantCommand,
    ConfirmShiftParticipantHandler,
)
from app.application.commands.reservation_outbox import ProcessReservationOutboxHandler
from app.application.commands.projects import (
    ApproveProjectMemberInvitationCommand,
    ApproveProjectMemberInvitationHandler,
    CreateProjectCommand,
    CreateProjectHandler,
    DeleteProjectCommand,
    DeleteProjectHandler,
    RemoveProjectMemberCommand,
    RemoveProjectMemberHandler,
    UpdateProjectCommand,
    UpdateProjectHandler,
)
from app.application.ports.domain import (
    StoredFile,
    UserResourceItem,
    UserResourceTimeWindow,
)
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
from app.domain.entities import (
    Document,
    Project,
    ProjectMember,
    ReservationOutboxMessage,
    Shift,
    ShiftParticipant,
    ShiftResourceRequest,
)
from app.domain.enums import (
    DocumentStatus,
    DocumentType,
    ProjectMemberStatus,
    ProjectRole,
    ProjectStatus,
    ShiftParticipantStatus,
    ShiftStatus,
)
from app.domain.errors.business import (
    AccessDeniedError,
    EntityNotFoundError,
    ExternalServiceError,
    StateTransitionError,
)
from app.domain.policy.member_access import ActiveMemberPolicy, DirectorMemberPolicy
from app.domain.services import (
    ProjectMembershipService,
    ResourceRequestService,
    ShiftParticipantService,
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
        self.resources: dict[tuple[UUID, str], list[UserResourceItem]] = {}
        self.request_ids: list[UUID] = []

    async def ensure_user_exists(self, user_id: UUID) -> None:
        self.existing_users.add(user_id)

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
    ) -> UUID:
        self.request_ids.append(request_id)
        if self.fail_reserve_user:
            raise RuntimeError("reserve failed")
        return uuid4()

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
    ) -> UUID:
        self.request_ids.append(request_id)
        return uuid4()

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
    async def upload(self, *, filename: str, content: bytes, content_type: str) -> StoredFile:
        return StoredFile(
            bucket="bucket",
            storage_key=f"key-{filename}",
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

    async def update(self, document: Document) -> None:
        self.data[document.oid] = document


class InMemoryResourceRequestRepo:
    def __init__(self) -> None:
        self.data: dict[UUID, ShiftResourceRequest] = {}

    async def add(self, request: ShiftResourceRequest) -> None:
        self.data[request.oid] = request

    async def get_by_id(self, request_id: UUID) -> ShiftResourceRequest | None:
        return self.data.get(request_id)

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
    storage = FakeStorage()
    clock = SystemClock()
    reservation_processor = ProcessReservationOutboxHandler(
        transaction_manager=tx,
        clock=clock,
        publisher=publisher,
        user_service=user_service,
        shifts=shifts,
        shift_participants=participants,
        resource_requests=requests,
        reservation_outbox=reservation_outbox,
        shift_participant_service=ShiftParticipantService(),
        resource_request_service=ResourceRequestService(),
    )

    create_project_handler = CreateProjectHandler(
        transaction_manager=tx,
        clock=clock,
        id_generator=id_generator or FakeIdGenerator(),
        publisher=publisher,
        user_service=user_service,
        projects=projects,
        project_members=members,
        membership_service=ProjectMembershipService(),
    )
    confirm_participant_handler = ConfirmShiftParticipantHandler(
        transaction_manager=tx,
        clock=clock,
        publisher=publisher,
        user_service=user_service,
        reservation_outbox=reservation_outbox,
        reservation_processor=reservation_processor,
        shifts=shifts,
        shift_participants=participants,
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


def test_confirm_participant_marks_reserve_failed_on_external_error() -> None:
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
        ) = build_context(fail_reserve_user=True)
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

        with pytest.raises(ExternalServiceError):
            await confirm_participant_handler(
                ConfirmShiftParticipantCommand(
                    participant_id=participant.oid,
                    actor_user_id=participant_user_id,
                )
            )

        updated = await participants.get_by_id(participant.oid)
        assert updated is not None
        assert updated.status == ShiftParticipantStatus.RESERVE_FAILED
        assert tx.commits == 2
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
