import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from app.application.commands.reservation_outbox import (
    OUTBOX_STATUS_PENDING,
    PARTICIPANT_RESERVE_OPERATION,
    RESOURCE_RESERVE_OPERATION,
    ProcessReservationOutboxHandler,
)
from app.application.commands.reservation_events import (
    HandleParticipantReservationCheckSucceededCommand,
    HandleParticipantReservationCheckSucceededHandler,
    HandleResourceReservationCheckSucceededCommand,
    HandleResourceReservationCheckSucceededHandler,
)
from app.domain.entities import (
    Project,
    ProjectMember,
    ReservationOutboxMessage,
    Shift,
    ShiftParticipant,
    ShiftResourceRequest,
)
from app.domain.enums import ProjectMemberStatus, ProjectRole, ProjectStatus, ShiftStatus
from app.presentation.schemas import to_project_role_input


def test_to_project_role_input_accepts_raw_int_from_orm() -> None:
    assert to_project_role_input(int(ProjectRole.SOUND)).value == "SOUND"


class FakeTx:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


class FakeClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class FakePublisher:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, topic: str, payload: dict) -> None:
        self.events.append((topic, payload))


class FakeUserService:
    def __init__(self) -> None:
        self.request_ids: list = []

    async def reserve_user_time(
        self,
        *,
        request_id,
        user_id,
        time_from,
        time_to,
        project_id,
        shift_id,
        entity_id,
    ) -> None:
        self.request_ids.append(request_id)

    async def reserve_resource_time(
        self,
        *,
        request_id,
        owner_user_id,
        resource_id,
        time_from,
        time_to,
        project_id,
        shift_id,
        entity_id,
    ) -> None:
        self.request_ids.append(request_id)


class InMemoryShiftRepo:
    def __init__(self) -> None:
        self.data: dict = {}

    async def get_by_id(self, shift_id):
        return self.data.get(shift_id)


class InMemoryProjectRepo:
    def __init__(self) -> None:
        self.data: dict = {}

    async def get_by_id(self, project_id):
        return self.data.get(project_id)


class InMemoryParticipantRepo:
    def __init__(self) -> None:
        self.by_id: dict = {}
        self.by_shift_user: dict = {}

    async def get_by_id(self, participant_id):
        return self.by_id.get(participant_id)


class InMemoryResourceRequestRepo:
    def __init__(self) -> None:
        self.data: dict = {}

    async def get_by_id(self, request_id):
        return self.data.get(request_id)


class InMemoryReservationOutboxRepo:
    def __init__(self) -> None:
        self.data: dict = {}

    async def get_by_id(self, message_id):
        return self.data.get(message_id)

    async def update(self, message) -> None:
        self.data[message.oid] = message


def test_project_member_role_can_be_plain_int() -> None:
    member = ProjectMember(
        oid=uuid4(),
        project_id=uuid4(),
        user_id=uuid4(),
        role=int(ProjectRole.CAMERA),
        status=ProjectMemberStatus.ACTIVE,
        invited_by=uuid4(),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    assert to_project_role_input(member.role).value == "CAMERA"


def test_outbox_handler_accepts_plain_int_participant_status() -> None:
    now = datetime.now(UTC)
    participant = ShiftParticipant(
        oid=uuid4(),
        shift_id=uuid4(),
        user_id=uuid4(),
        role=ProjectRole.SOUND,
        time_from=now,
        time_to=now,
        status=15,
        user_reservation_id=None,
        reserve_failure_reason=None,
        added_by=uuid4(),
        created_at=now,
        updated_at=now,
    )
    shift_repo = InMemoryShiftRepo()
    shift_repo.data[participant.shift_id] = Shift(
        oid=participant.shift_id,
        project_id=uuid4(),
        title="Shift",
        description="",
        start_time=now,
        end_time=now,
        status=ShiftStatus.DRAFT,
        created_by=uuid4(),
        approved_by=None,
        approved_at=None,
        created_at=now,
        updated_at=now,
    )
    outbox_message = ReservationOutboxMessage(
        oid=uuid4(),
        operation=PARTICIPANT_RESERVE_OPERATION,
        aggregate_id=participant.oid,
        status=OUTBOX_STATUS_PENDING,
        attempts=0,
        last_error=None,
        created_at=now,
        updated_at=now,
    )
    participants = InMemoryParticipantRepo()
    participants.by_id[participant.oid] = participant
    participants.by_shift_user[(participant.shift_id, participant.user_id)] = participant
    outbox = InMemoryReservationOutboxRepo()
    outbox.data[outbox_message.oid] = outbox_message
    user_service = FakeUserService()
    handler = ProcessReservationOutboxHandler(
        transaction_manager=FakeTx(),
        clock=FakeClock(),
        publisher=FakePublisher(),
        user_service=user_service,
        shifts=shift_repo,
        shift_participants=participants,
        resource_requests=InMemoryResourceRequestRepo(),
        reservation_outbox=outbox,
    )

    result = asyncio.run(handler.process_message(outbox_message.oid))

    assert result.status == "completed"
    assert outbox.data[outbox_message.oid].status == "completed"
    assert user_service.request_ids == [outbox_message.oid]


def test_outbox_handler_accepts_plain_int_resource_request_status() -> None:
    now = datetime.now(UTC)
    request = ShiftResourceRequest(
        oid=uuid4(),
        project_id=uuid4(),
        shift_id=uuid4(),
        resource_type="microfons",
        resource_id=uuid4(),
        resource_owner_user_id=uuid4(),
        requested_by_user_id=uuid4(),
        time_from=now,
        time_to=now,
        status=15,
        resource_reservation_id=None,
        rejection_reason=None,
        reserve_failure_reason=None,
        created_at=now,
        updated_at=now,
    )
    outbox_message = ReservationOutboxMessage(
        oid=uuid4(),
        operation=RESOURCE_RESERVE_OPERATION,
        aggregate_id=request.oid,
        status=OUTBOX_STATUS_PENDING,
        attempts=0,
        last_error=None,
        created_at=now,
        updated_at=now,
    )
    outbox = InMemoryReservationOutboxRepo()
    outbox.data[outbox_message.oid] = outbox_message
    requests = InMemoryResourceRequestRepo()
    requests.data[request.oid] = request
    user_service = FakeUserService()
    handler = ProcessReservationOutboxHandler(
        transaction_manager=FakeTx(),
        clock=FakeClock(),
        publisher=FakePublisher(),
        user_service=user_service,
        shifts=InMemoryShiftRepo(),
        shift_participants=InMemoryParticipantRepo(),
        resource_requests=requests,
        reservation_outbox=outbox,
    )

    result = asyncio.run(handler.process_message(outbox_message.oid))

    assert result.status == "completed"
    assert outbox.data[outbox_message.oid].status == "completed"
    assert user_service.request_ids == [outbox_message.oid]


def test_reservation_event_handler_accepts_plain_int_participant_status() -> None:
    now = datetime.now(UTC)
    project_id = uuid4()
    participant = ShiftParticipant(
        oid=uuid4(),
        shift_id=uuid4(),
        user_id=uuid4(),
        role=ProjectRole.SOUND,
        time_from=now,
        time_to=now,
        status=15,
        user_reservation_id=None,
        reserve_failure_reason=None,
        added_by=uuid4(),
        created_at=now,
        updated_at=now,
    )
    participants = InMemoryParticipantRepo()
    participants.by_id[participant.oid] = participant
    projects = InMemoryProjectRepo()
    projects.data[project_id] = Project(
        oid=project_id,
        title="Project",
        description="",
        owner_id=uuid4(),
        status=ProjectStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    shifts = InMemoryShiftRepo()
    shifts.data[participant.shift_id] = Shift(
        oid=participant.shift_id,
        project_id=project_id,
        title="Shift",
        description="",
        start_time=now,
        end_time=now,
        status=ShiftStatus.DRAFT,
        created_by=uuid4(),
        approved_by=None,
        approved_at=None,
        created_at=now,
        updated_at=now,
    )
    publisher = FakePublisher()
    handler = HandleParticipantReservationCheckSucceededHandler(
        publisher=publisher,
        projects=projects,
        shifts=shifts,
        shift_participants=participants,
    )

    asyncio.run(
        handler(
            HandleParticipantReservationCheckSucceededCommand(
                request_id=uuid4(),
                project_id=project_id,
                shift_id=participant.shift_id,
                participant_id=participant.oid,
                user_id=participant.user_id,
            )
        )
    )

    assert publisher.events
    assert publisher.events[0][0] == "shift.participant_approval_requested"


def test_reservation_event_handler_accepts_plain_int_resource_status() -> None:
    now = datetime.now(UTC)
    project_id = uuid4()
    request = ShiftResourceRequest(
        oid=uuid4(),
        project_id=project_id,
        shift_id=uuid4(),
        resource_type="microfons",
        resource_id=uuid4(),
        resource_owner_user_id=uuid4(),
        requested_by_user_id=uuid4(),
        time_from=now,
        time_to=now,
        status=15,
        resource_reservation_id=None,
        rejection_reason=None,
        reserve_failure_reason=None,
        created_at=now,
        updated_at=now,
    )
    requests = InMemoryResourceRequestRepo()
    requests.data[request.oid] = request
    projects = InMemoryProjectRepo()
    projects.data[project_id] = Project(
        oid=project_id,
        title="Project",
        description="",
        owner_id=uuid4(),
        status=ProjectStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    shifts = InMemoryShiftRepo()
    shifts.data[request.shift_id] = Shift(
        oid=request.shift_id,
        project_id=project_id,
        title="Shift",
        description="",
        start_time=now,
        end_time=now,
        status=ShiftStatus.DRAFT,
        created_by=uuid4(),
        approved_by=None,
        approved_at=None,
        created_at=now,
        updated_at=now,
    )
    publisher = FakePublisher()
    handler = HandleResourceReservationCheckSucceededHandler(
        publisher=publisher,
        projects=projects,
        shifts=shifts,
        resource_requests=requests,
    )

    asyncio.run(
        handler(
            HandleResourceReservationCheckSucceededCommand(
                request_id=uuid4(),
                project_id=request.project_id,
                shift_id=request.shift_id,
                resource_request_id=request.oid,
                owner_user_id=request.resource_owner_user_id,
                resource_id=request.resource_id,
            )
        )
    )

    assert publisher.events
    assert publisher.events[0][0] == "shift.resource_request_approval_requested"
