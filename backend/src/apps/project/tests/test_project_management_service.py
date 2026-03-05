import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.application.commands.participants import (
    ConfirmShiftParticipantCommand,
    ConfirmShiftParticipantHandler,
)
from app.application.commands.projects import CreateProjectCommand, CreateProjectHandler
from app.application.ports.domain import StoredFile
from app.application.queries.documents import (
    GetDocumentDownloadUrlHandler,
    GetDocumentDownloadUrlQuery,
)
from app.application.support import SystemClock
from app.domain.entities import (
    Document,
    Project,
    ProjectMember,
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
from app.domain.services import (
    ProjectMembershipService,
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

    async def ensure_user_exists(self, user_id: UUID) -> None:
        self.existing_users.add(user_id)

    async def reserve_user_time(
        self,
        *,
        user_id: UUID,
        time_from: datetime,
        time_to: datetime,
        project_id: UUID,
        shift_id: UUID,
        entity_id: UUID,
    ) -> UUID:
        if self.fail_reserve_user:
            raise RuntimeError("reserve failed")
        return uuid4()

    async def reserve_resource_time(
        self,
        *,
        owner_user_id: UUID,
        resource_id: UUID,
        time_from: datetime,
        time_to: datetime,
        project_id: UUID,
        shift_id: UUID,
        entity_id: UUID,
    ) -> UUID:
        return uuid4()


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

    async def update(self, project: Project) -> None:
        self.data[project.oid] = project


class InMemoryProjectMemberRepo:
    def __init__(self) -> None:
        self.data: dict[tuple[UUID, UUID], ProjectMember] = {}

    async def add(self, member: ProjectMember) -> None:
        self.data[(member.project_id, member.user_id)] = member

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
    storage = FakeStorage()
    clock = SystemClock()

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

        with pytest.raises(RuntimeError):
            await confirm_participant_handler(
                ConfirmShiftParticipantCommand(
                    participant_id=participant.oid,
                    actor_user_id=participant_user_id,
                )
            )

        updated = await participants.get_by_id(participant.oid)
        assert updated is not None
        assert updated.status == ShiftParticipantStatus.RESERVE_FAILED
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
