import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.application.commands.reservation_events import (
    HandleParticipantReservationCheckFailedCommand,
    HandleParticipantReservationCheckFailedHandler,
    HandleParticipantReservationCheckSucceededCommand,
    HandleParticipantReservationCheckSucceededHandler,
    HandleResourceReservationCheckSucceededCommand,
    HandleResourceReservationCheckSucceededHandler,
    HandleResourceReservationSucceededCommand,
    HandleResourceReservationSucceededHandler,
    PARTICIPANT_APPROVAL_REQUESTED_TOPIC,
    RESOURCE_APPROVAL_REQUESTED_TOPIC,
)
from app.application.commands.reservation_outbox import (
    OUTBOX_STATUS_PENDING,
    PARTICIPANT_RESERVE_OPERATION,
    ProcessReservationOutboxHandler,
)
from app.domain.entities import Project, ReservationOutboxMessage, Shift, ShiftParticipant, ShiftResourceRequest
from app.domain.enums import (
    ProjectRole,
    ProjectStatus,
    ResourceRequestStatus,
    ShiftParticipantStatus,
    ShiftStatus,
)
from app.domain.services import ResourceRequestService, ShiftParticipantService


def now_utc() -> datetime:
    return datetime.now(tz=UTC)


class FakeTx:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        raise AssertionError("rollback should not be called")


class FakeClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class FakePublisher:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, topic: str, payload: dict) -> None:
        self.events.append((topic, payload))


class FakeUserService:
    def __init__(self) -> None:
        self.participant_calls: list[dict] = []
        self.resource_calls: list[dict] = []

    async def ensure_user_exists(self, user_id: UUID) -> None:
        raise AssertionError("not used")

    async def list_user_resources(self, *, user_id: UUID, resource_kinds: tuple[str, ...]):
        raise AssertionError("not used")

    async def reserve_user_time(self, **kwargs) -> None:
        self.participant_calls.append(kwargs)

    async def reserve_resource_time(self, **kwargs) -> None:
        self.resource_calls.append(kwargs)


class FakeProjectRepo:
    def __init__(self, items: list[Project] | None = None) -> None:
        self.data = {item.oid: item for item in items or []}

    async def get_by_id(self, project_id: UUID) -> Project | None:
        return self.data.get(project_id)


class FakeShiftRepo:
    def __init__(self, items: list[Shift] | None = None) -> None:
        self.data = {item.oid: item for item in items or []}

    async def get_by_id(self, shift_id: UUID) -> Shift | None:
        return self.data.get(shift_id)


class FakeParticipantRepo:
    def __init__(self, items: list[ShiftParticipant] | None = None) -> None:
        self.data = {item.oid: item for item in items or []}
        self.updated: list[ShiftParticipant] = []

    async def get_by_id(self, participant_id: UUID) -> ShiftParticipant | None:
        return self.data.get(participant_id)

    async def update(self, participant: ShiftParticipant) -> None:
        self.data[participant.oid] = participant
        self.updated.append(participant)


class FakeResourceRequestRepo:
    def __init__(self, items: list[ShiftResourceRequest] | None = None) -> None:
        self.data = {item.oid: item for item in items or []}
        self.updated: list[ShiftResourceRequest] = []

    async def get_by_id(self, request_id: UUID) -> ShiftResourceRequest | None:
        return self.data.get(request_id)

    async def update(self, request: ShiftResourceRequest) -> None:
        self.data[request.oid] = request
        self.updated.append(request)


class FakeOutboxRepo:
    def __init__(self, items: list[ReservationOutboxMessage] | None = None) -> None:
        self.data = {item.oid: item for item in items or []}

    async def get_by_id(self, message_id: UUID) -> ReservationOutboxMessage | None:
        return self.data.get(message_id)

    async def list_pending(self, *, limit: int) -> list[ReservationOutboxMessage]:
        return [item for item in self.data.values() if item.status == OUTBOX_STATUS_PENDING][:limit]

    async def update(self, message: ReservationOutboxMessage) -> None:
        self.data[message.oid] = message


def test_process_reservation_outbox_dispatches_participant_check_request() -> None:
    async def scenario() -> None:
        now = now_utc()
        project_id = uuid4()
        shift = Shift(
            oid=uuid4(),
            project_id=project_id,
            title="Shift",
            description="Desc",
            start_time=now,
            end_time=now + timedelta(hours=3),
            status=ShiftStatus.DRAFT,
            created_by=uuid4(),
            created_at=now,
            updated_at=now,
        )
        participant = ShiftParticipant(
            oid=uuid4(),
            shift_id=shift.oid,
            user_id=uuid4(),
            role=ProjectRole.CAMERA,
            time_from=now + timedelta(minutes=15),
            time_to=now + timedelta(hours=1),
            status=ShiftParticipantStatus.RESERVING,
            added_by=uuid4(),
            created_at=now,
            updated_at=now,
        )
        message = ReservationOutboxMessage(
            oid=uuid4(),
            operation=PARTICIPANT_RESERVE_OPERATION,
            aggregate_id=participant.oid,
            status=OUTBOX_STATUS_PENDING,
            attempts=0,
            created_at=now,
            updated_at=now,
        )
        tx = FakeTx()
        user_service = FakeUserService()
        outbox = FakeOutboxRepo([message])
        handler = ProcessReservationOutboxHandler(
            transaction_manager=tx,
            clock=FakeClock(now),
            publisher=FakePublisher(),
            user_service=user_service,
            shifts=FakeShiftRepo([shift]),
            shift_participants=FakeParticipantRepo([participant]),
            resource_requests=FakeResourceRequestRepo(),
            reservation_outbox=outbox,
        )

        result = await handler.process_message(message.oid)

        assert result.status == "completed"
        assert user_service.participant_calls == [
            {
                "request_id": message.oid,
                "user_id": participant.user_id,
                "time_from": participant.time_from,
                "time_to": participant.time_to,
                "project_id": project_id,
                "shift_id": shift.oid,
                "entity_id": participant.oid,
            }
        ]
        assert outbox.data[message.oid].status == "completed"
        assert outbox.data[message.oid].attempts == 1
        assert tx.commits == 1

    asyncio.run(scenario())


def test_participant_check_success_publishes_approval_request_contract() -> None:
    async def scenario() -> None:
        now = now_utc()
        project = Project(
            oid=uuid4(),
            title="Feature film",
            description="Desc",
            owner_id=uuid4(),
            status=ProjectStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        shift = Shift(
            oid=uuid4(),
            project_id=project.oid,
            title="Night shoot",
            description="Desc",
            start_time=now,
            end_time=now + timedelta(hours=3),
            status=ShiftStatus.APPROVED,
            created_by=uuid4(),
            created_at=now,
            updated_at=now,
        )
        participant = ShiftParticipant(
            oid=uuid4(),
            shift_id=shift.oid,
            user_id=uuid4(),
            role=ProjectRole.ACTOR,
            time_from=now,
            time_to=now + timedelta(hours=1),
            status=ShiftParticipantStatus.RESERVING,
            added_by=uuid4(),
            created_at=now,
            updated_at=now,
        )
        publisher = FakePublisher()
        handler = HandleParticipantReservationCheckSucceededHandler(
            publisher=publisher,
            projects=FakeProjectRepo([project]),
            shifts=FakeShiftRepo([shift]),
            shift_participants=FakeParticipantRepo([participant]),
        )
        command = HandleParticipantReservationCheckSucceededCommand(
            request_id=uuid4(),
            project_id=project.oid,
            shift_id=participant.shift_id,
            participant_id=participant.oid,
            user_id=participant.user_id,
        )

        await handler(command)

        assert publisher.events[0][0] == PARTICIPANT_APPROVAL_REQUESTED_TOPIC
        assert publisher.events[0][1]["participant_id"] == str(participant.oid)
        assert publisher.events[0][1]["project_title"] == project.title
        assert publisher.events[0][1]["shift_title"] == shift.title
        assert publisher.events[0][1]["role"] == "ACTOR"

    asyncio.run(scenario())


def test_participant_check_failed_marks_participant_failed() -> None:
    async def scenario() -> None:
        now = now_utc()
        participant = ShiftParticipant(
            oid=uuid4(),
            shift_id=uuid4(),
            user_id=uuid4(),
            role=ProjectRole.ACTOR,
            time_from=now,
            time_to=now + timedelta(hours=1),
            status=ShiftParticipantStatus.RESERVING,
            added_by=uuid4(),
            created_at=now,
            updated_at=now,
        )
        tx = FakeTx()
        repo = FakeParticipantRepo([participant])
        handler = HandleParticipantReservationCheckFailedHandler(
            transaction_manager=tx,
            clock=FakeClock(now),
            shift_participants=repo,
            shift_participant_service=ShiftParticipantService(),
        )

        await handler(
            HandleParticipantReservationCheckFailedCommand(
                participant_id=participant.oid,
                reason="No free window",
            )
        )

        assert repo.data[participant.oid].status == ShiftParticipantStatus.RESERVE_FAILED
        assert repo.data[participant.oid].reserve_failure_reason == "No free window"
        assert tx.commits == 1

    asyncio.run(scenario())


def test_resource_check_success_publishes_approval_request_contract() -> None:
    async def scenario() -> None:
        now = now_utc()
        project = Project(
            oid=uuid4(),
            title="Feature film",
            description="Desc",
            owner_id=uuid4(),
            status=ProjectStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        shift = Shift(
            oid=uuid4(),
            project_id=project.oid,
            title="Night shoot",
            description="Desc",
            start_time=now,
            end_time=now + timedelta(hours=3),
            status=ShiftStatus.APPROVED,
            created_by=uuid4(),
            created_at=now,
            updated_at=now,
        )
        request = ShiftResourceRequest(
            oid=uuid4(),
            project_id=project.oid,
            shift_id=shift.oid,
            resource_type="camera",
            resource_id=uuid4(),
            resource_owner_user_id=uuid4(),
            requested_by_user_id=uuid4(),
            time_from=now,
            time_to=now + timedelta(hours=2),
            status=ResourceRequestStatus.RESERVING,
            created_at=now,
            updated_at=now,
        )
        publisher = FakePublisher()
        handler = HandleResourceReservationCheckSucceededHandler(
            publisher=publisher,
            projects=FakeProjectRepo([project]),
            shifts=FakeShiftRepo([shift]),
            resource_requests=FakeResourceRequestRepo([request]),
        )

        await handler(
            HandleResourceReservationCheckSucceededCommand(
                request_id=uuid4(),
                project_id=request.project_id,
                shift_id=request.shift_id,
                resource_request_id=request.oid,
                owner_user_id=request.resource_owner_user_id,
                resource_id=request.resource_id,
            )
        )

        assert publisher.events[0][0] == RESOURCE_APPROVAL_REQUESTED_TOPIC
        assert publisher.events[0][1]["resource_type"] == request.resource_type
        assert publisher.events[0][1]["project_title"] == project.title
        assert publisher.events[0][1]["shift_title"] == shift.title

    asyncio.run(scenario())


def test_resource_reserved_event_marks_request_reserved_and_publishes_domain_event() -> None:
    async def scenario() -> None:
        now = now_utc()
        request = ShiftResourceRequest(
            oid=uuid4(),
            project_id=uuid4(),
            shift_id=uuid4(),
            resource_type="light",
            resource_id=uuid4(),
            resource_owner_user_id=uuid4(),
            requested_by_user_id=uuid4(),
            time_from=now,
            time_to=now + timedelta(hours=2),
            status=ResourceRequestStatus.RESERVING,
            created_at=now,
            updated_at=now,
        )
        reservation_id = uuid4()
        tx = FakeTx()
        publisher = FakePublisher()
        repo = FakeResourceRequestRepo([request])
        handler = HandleResourceReservationSucceededHandler(
            transaction_manager=tx,
            clock=FakeClock(now),
            publisher=publisher,
            resource_requests=repo,
            resource_request_service=ResourceRequestService(),
        )

        await handler(
            HandleResourceReservationSucceededCommand(
                project_id=request.project_id,
                shift_id=request.shift_id,
                resource_request_id=request.oid,
                reservation_id=reservation_id,
            )
        )

        assert repo.data[request.oid].status == ResourceRequestStatus.RESERVED
        assert repo.data[request.oid].resource_reservation_id == reservation_id
        assert publisher.events[0][0] == "shift.resource_request_reserved"
        assert tx.commits == 1

    asyncio.run(scenario())
