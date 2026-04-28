import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt

from app.application.commands.approval_notifications import (
    HandleProjectMemberInvitationRequestedCommand,
    HandleProjectMemberInvitationRequestedHandler,
    HandleParticipantApprovalRequestedCommand,
    HandleParticipantApprovalRequestedHandler,
)
from app.application.commands.confirm_project_invitation import (
    ConfirmProjectInvitationByTokenHandler,
)
from app.application.commands.confirm_reservation import ConfirmReservationByTokenHandler
from app.application.ports.approvals import (
    ParticipantApprovalState,
    ProjectMemberInvitationTokenData,
)
from app.config import ConfirmationSettings
from app.infrastructure.security.confirmation_token import JWTConfirmationTokenService
from test.helpers import FakeEntityRepository, make_user


def now_utc() -> datetime:
    return datetime.now(tz=UTC)


class FakePublisher:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, topic: str, payload: dict) -> None:
        self.events.append((topic, payload))


class FakeProjectApprovalStates:
    def __init__(self, participant_state: ParticipantApprovalState) -> None:
        self.participant_state = participant_state

    async def get_participant_approval_state(self, *, participant_id):
        assert participant_id == self.participant_state.participant_id
        return self.participant_state

    async def get_resource_approval_state(self, *, resource_request_id):
        raise AssertionError("resource flow not used")


class FakeReserveAvailabilityHandler:
    def __init__(self, reservation_id) -> None:
        self.reservation_id = reservation_id
        self.commands = []

    async def __call__(self, command):
        self.commands.append(command)
        return self.reservation_id


def _settings(ttl_hours: int = 24) -> ConfirmationSettings:
    return ConfirmationSettings(
        CONFIRMATION_SECRET_KEY="test-secret-key-that-is-long-enough",
        CONFIRMATION_TTL_HOURS=ttl_hours,
        PUBLIC_BASE_URL="http://localhost:8000",
        CONFIRMATION_ALGORITHM="HS256",
    )


def test_participant_approval_request_publishes_email_event() -> None:
    async def scenario() -> None:
        settings = _settings()
        user_id = uuid4()
        handler = HandleParticipantApprovalRequestedHandler(
            users=FakeEntityRepository([make_user(user_id)]),
            publisher=FakePublisher(),
            confirmation_tokens=JWTConfirmationTokenService(settings),
            confirmation=settings,
        )
        publisher = handler._publisher  # type: ignore[attr-defined]
        now = now_utc()

        await handler(
            HandleParticipantApprovalRequestedCommand(
                request_id=uuid4(),
                project_id=uuid4(),
                project_title="Feature film",
                shift_id=uuid4(),
                shift_title="Night shoot",
                participant_id=uuid4(),
                user_id=user_id,
                role="ACTOR",
                time_from=now,
                time_to=now + timedelta(hours=1),
            )
        )

        assert publisher.events[0][0] == "notification.email_requested"
        event = publisher.events[0][1]
        assert event["template"] == "reservation_confirmation"
        assert event["payload"]["project_title"] == "Feature film"
        assert event["payload"]["role"] == "ACTOR"
        assert event["payload"]["confirm_url"].startswith("http://localhost:8000/user/confirmations/")

    asyncio.run(scenario())


def test_project_member_invitation_request_publishes_email_event() -> None:
    async def scenario() -> None:
        settings = _settings()
        user_id = uuid4()
        handler = HandleProjectMemberInvitationRequestedHandler(
            users=FakeEntityRepository([make_user(user_id)]),
            publisher=FakePublisher(),
            confirmation_tokens=JWTConfirmationTokenService(settings),
            confirmation=settings,
        )
        publisher = handler._publisher  # type: ignore[attr-defined]

        await handler(
            HandleProjectMemberInvitationRequestedCommand(
                request_id=uuid4(),
                project_id=uuid4(),
                project_title="Feature film",
                member_id=uuid4(),
                user_id=user_id,
                role="CAMERA",
                invited_by_user_id=uuid4(),
            )
        )

        assert publisher.events[0][0] == "notification.email_requested"
        event = publisher.events[0][1]
        assert event["template"] == "project_member_invitation"
        assert event["payload"]["project_title"] == "Feature film"
        assert event["payload"]["role"] == "CAMERA"
        assert event["payload"]["accept_url"].startswith(
            "http://localhost:8000/user/project-invitations/"
        )

    asyncio.run(scenario())


def test_confirmation_token_service_detects_tampered_and_expired_tokens() -> None:
    settings = _settings()
    service = JWTConfirmationTokenService(settings)
    token = service.issue_participant_token(
        request_id=uuid4(),
        project_id=uuid4(),
        shift_id=uuid4(),
        participant_id=uuid4(),
        user_id=uuid4(),
        time_from=now_utc(),
        time_to=now_utc() + timedelta(hours=1),
    )

    valid = service.decode_confirmation_token(token)
    assert valid.request_id is not None

    tampered = token + "broken"
    invalid_handler = ConfirmReservationByTokenHandler(
        confirmation_tokens=service,
        project_approval_states=FakeProjectApprovalStates(
            participant_state=ParticipantApprovalState(
                request_id=uuid4(),
                project_id=uuid4(),
                project_title="x",
                shift_id=uuid4(),
                shift_title="x",
                participant_id=uuid4(),
                user_id=uuid4(),
                role="ACTOR",
                time_from=now_utc(),
                time_to=now_utc() + timedelta(hours=1),
                status=15,
                status_name="RESERVING",
                user_reservation_id=None,
                reserve_failure_reason=None,
            )
        ),
        reserve_availability=FakeReserveAvailabilityHandler(uuid4()),
        publisher=FakePublisher(),
    )
    invalid = asyncio.run(invalid_handler(tampered))
    assert invalid.page == "invalid"

    expired_token = jwt.encode(
        payload={
            "type": "participant_approval",
            "request_id": str(uuid4()),
            "project_id": str(uuid4()),
            "shift_id": str(uuid4()),
            "participant_id": str(uuid4()),
            "user_id": str(uuid4()),
            "time_from": now_utc().isoformat(),
            "time_to": (now_utc() + timedelta(hours=1)).isoformat(),
            "iat": int((now_utc() - timedelta(hours=2)).timestamp()),
            "exp": int((now_utc() - timedelta(hours=1)).timestamp()),
        },
        key=settings.secret_key,
        algorithm=settings.algorithm,
    )
    expired = asyncio.run(invalid_handler(expired_token))
    assert expired.page == "expired"


def test_project_member_invitation_token_decodes_project_invitation_payload() -> None:
    settings = _settings()
    service = JWTConfirmationTokenService(settings)
    request_id = uuid4()
    project_id = uuid4()
    member_id = uuid4()
    user_id = uuid4()

    token = service.issue_project_member_invitation_token(
        request_id=request_id,
        project_id=project_id,
        member_id=member_id,
        user_id=user_id,
        role="ACTOR",
    )

    payload = service.decode_confirmation_token(token)

    assert isinstance(payload, ProjectMemberInvitationTokenData)
    assert payload.request_id == request_id
    assert payload.project_id == project_id
    assert payload.member_id == member_id
    assert payload.user_id == user_id
    assert payload.role == "ACTOR"


def test_confirm_project_invitation_requires_matching_logged_in_user() -> None:
    async def scenario() -> None:
        settings = _settings()
        token_service = JWTConfirmationTokenService(settings)
        invited_user_id = uuid4()
        token = token_service.issue_project_member_invitation_token(
            request_id=uuid4(),
            project_id=uuid4(),
            member_id=uuid4(),
            user_id=invited_user_id,
            role="ACTOR",
        )
        publisher = FakePublisher()
        handler = ConfirmProjectInvitationByTokenHandler(
            confirmation_tokens=token_service,
            publisher=publisher,
        )

        mismatch = await handler(token=token, actor_user_id=uuid4())
        accepted = await handler(token=token, actor_user_id=invited_user_id)

        assert mismatch.page == "invalid"
        assert accepted.page == "success"
        assert publisher.events == [
            (
                "project.member.approved",
                {
                    "project_id": str(
                        token_service.decode_confirmation_token(token).project_id
                    ),
                    "user_id": str(invited_user_id),
                    "approved_by_user_id": str(invited_user_id),
                },
            )
        ]

    asyncio.run(scenario())


def test_confirm_reservation_handler_reserves_and_publishes_success_event() -> None:
    async def scenario() -> None:
        settings = _settings()
        token_service = JWTConfirmationTokenService(settings)
        request_id = uuid4()
        project_id = uuid4()
        shift_id = uuid4()
        participant_id = uuid4()
        user_id = uuid4()
        time_from = now_utc()
        time_to = time_from + timedelta(hours=1)
        token = token_service.issue_participant_token(
            request_id=request_id,
            project_id=project_id,
            shift_id=shift_id,
            participant_id=participant_id,
            user_id=user_id,
            time_from=time_from,
            time_to=time_to,
        )
        publisher = FakePublisher()
        reservation_id = uuid4()
        reserve_handler = FakeReserveAvailabilityHandler(reservation_id)
        handler = ConfirmReservationByTokenHandler(
            confirmation_tokens=token_service,
            project_approval_states=FakeProjectApprovalStates(
                participant_state=ParticipantApprovalState(
                    request_id=request_id,
                    project_id=project_id,
                    project_title="Feature film",
                    shift_id=shift_id,
                    shift_title="Night shoot",
                    participant_id=participant_id,
                    user_id=user_id,
                    role="ACTOR",
                    time_from=time_from,
                    time_to=time_to,
                    status=15,
                    status_name="RESERVING",
                    user_reservation_id=None,
                    reserve_failure_reason=None,
                )
            ),
            reserve_availability=reserve_handler,
            publisher=publisher,
        )

        result = await handler(token)

        assert result.page == "success"
        assert reserve_handler.commands[0].request_id == request_id
        assert publisher.events[0][0] == "shift.participant_reserved.user"
        assert publisher.events[0][1]["reservation_id"] == str(reservation_id)

    asyncio.run(scenario())


def test_confirm_reservation_handler_returns_already_processed_for_non_reserving_state() -> None:
    async def scenario() -> None:
        settings = _settings()
        token_service = JWTConfirmationTokenService(settings)
        request_id = uuid4()
        project_id = uuid4()
        shift_id = uuid4()
        participant_id = uuid4()
        user_id = uuid4()
        time_from = now_utc()
        time_to = time_from + timedelta(hours=1)
        token = token_service.issue_participant_token(
            request_id=request_id,
            project_id=project_id,
            shift_id=shift_id,
            participant_id=participant_id,
            user_id=user_id,
            time_from=time_from,
            time_to=time_to,
        )
        reserve_handler = FakeReserveAvailabilityHandler(uuid4())
        handler = ConfirmReservationByTokenHandler(
            confirmation_tokens=token_service,
            project_approval_states=FakeProjectApprovalStates(
                participant_state=ParticipantApprovalState(
                    request_id=request_id,
                    project_id=project_id,
                    project_title="Feature film",
                    shift_id=shift_id,
                    shift_title="Night shoot",
                    participant_id=participant_id,
                    user_id=user_id,
                    role="ACTOR",
                    time_from=time_from,
                    time_to=time_to,
                    status=20,
                    status_name="RESERVED",
                    user_reservation_id=uuid4(),
                    reserve_failure_reason=None,
                )
            ),
            reserve_availability=reserve_handler,
            publisher=FakePublisher(),
        )

        result = await handler(token)

        assert result.page == "already-processed"
        assert reserve_handler.commands == []

    asyncio.run(scenario())


def test_confirm_reservation_handler_returns_error_when_approval_state_lookup_fails() -> None:
    class FailingProjectApprovalStates:
        async def get_participant_approval_state(self, *, participant_id):
            raise RuntimeError("broker timeout")

        async def get_resource_approval_state(self, *, resource_request_id):
            raise AssertionError("resource flow not used")

    async def scenario() -> None:
        settings = _settings()
        token_service = JWTConfirmationTokenService(settings)
        token = token_service.issue_participant_token(
            request_id=uuid4(),
            project_id=uuid4(),
            shift_id=uuid4(),
            participant_id=uuid4(),
            user_id=uuid4(),
            time_from=now_utc(),
            time_to=now_utc() + timedelta(hours=1),
        )
        handler = ConfirmReservationByTokenHandler(
            confirmation_tokens=token_service,
            project_approval_states=FailingProjectApprovalStates(),
            reserve_availability=FakeReserveAvailabilityHandler(uuid4()),
            publisher=FakePublisher(),
        )

        result = await handler(token)

        assert result.page == "error"

    asyncio.run(scenario())
