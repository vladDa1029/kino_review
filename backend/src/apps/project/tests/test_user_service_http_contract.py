import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.application.ports.domain import UserResourceItem
from app.config import UserService
from app.domain.errors.business import EntityNotFoundError, ExternalServiceError
from app.infrastructure.broker.request_reply import BrokerReplyInbox
from app.presentation.http.user_service import UserServiceHttpClient


class FakePublisher:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, topic: str, payload: dict) -> None:
        self.events.append((topic, payload))


class ReplyingPublisher(FakePublisher):
    def __init__(self, inbox: BrokerReplyInbox, responder=None) -> None:
        super().__init__()
        self._inbox = inbox
        self._responder = responder

    async def publish(self, topic: str, payload: dict) -> None:
        await super().publish(topic, payload)
        if self._responder is None:
            return
        reply = self._responder(topic, payload)
        if reply is not None:
            self._inbox.resolve(payload["correlation_id"], reply)


class StubResourceClient(UserServiceHttpClient):
    def __init__(self, resources: list[UserResourceItem]) -> None:
        super().__init__(
            settings=_settings(),
            publisher=FakePublisher(),
            reply_inbox=BrokerReplyInbox(service_name="project", instance_id="test-instance"),
        )
        self._resources = resources

    async def list_user_resources(
        self,
        *,
        user_id,
        resource_kinds: tuple[str, ...],
    ) -> list[UserResourceItem]:
        return [
            item
            for item in self._resources
            if item.resource_kind in resource_kinds
        ]


def _settings(timeout_seconds: float = 1.0) -> UserService:
    return UserService(
        USER_SERVICE_BASE_URL="http://user.test",
        USER_SERVICE_TIMEOUT_SECONDS=timeout_seconds,
    )


def test_ensure_user_exists_publishes_existence_request_and_waits_for_reply() -> None:
    async def scenario() -> None:
        user_id = uuid4()
        inbox = BrokerReplyInbox(service_name="project", instance_id="test-instance")
        publisher = ReplyingPublisher(
            inbox=inbox,
            responder=lambda topic, payload: {
                "correlation_id": payload["correlation_id"],
                "response_type": "user.existence_provided",
                "user_id": payload["user_id"],
                "exists": True,
            },
        )
        client = UserServiceHttpClient(
            settings=_settings(),
            publisher=publisher,
            reply_inbox=inbox,
        )

        await client.ensure_user_exists(user_id)

        assert publisher.events[0][0] == "user.existence_requested"
        assert publisher.events[0][1]["reply_topic"] == inbox.reply_topic
        assert publisher.events[0][1]["user_id"] == str(user_id)

    asyncio.run(scenario())


def test_ensure_user_exists_raises_not_found_when_reply_reports_missing_user() -> None:
    async def scenario() -> None:
        user_id = uuid4()
        inbox = BrokerReplyInbox(service_name="project", instance_id="test-instance")
        publisher = ReplyingPublisher(
            inbox=inbox,
            responder=lambda topic, payload: {
                "correlation_id": payload["correlation_id"],
                "response_type": "user.existence_provided",
                "user_id": payload["user_id"],
                "exists": False,
            },
        )
        client = UserServiceHttpClient(
            settings=_settings(),
            publisher=publisher,
            reply_inbox=inbox,
        )

        with pytest.raises(EntityNotFoundError):
            await client.ensure_user_exists(user_id)

    asyncio.run(scenario())


def test_ensure_user_exists_raises_external_error_on_failed_reply() -> None:
    async def scenario() -> None:
        user_id = uuid4()
        inbox = BrokerReplyInbox(service_name="project", instance_id="test-instance")
        publisher = ReplyingPublisher(
            inbox=inbox,
            responder=lambda topic, payload: {
                "correlation_id": payload["correlation_id"],
                "response_type": "user.existence_failed",
                "user_id": payload["user_id"],
                "reason": "broker failure",
            },
        )
        client = UserServiceHttpClient(
            settings=_settings(),
            publisher=publisher,
            reply_inbox=inbox,
        )

        with pytest.raises(ExternalServiceError):
            await client.ensure_user_exists(user_id)

    asyncio.run(scenario())


def test_ensure_user_exists_raises_external_error_on_timeout_and_cleans_waiter() -> None:
    async def scenario() -> None:
        user_id = uuid4()
        inbox = BrokerReplyInbox(service_name="project", instance_id="test-instance")
        publisher = ReplyingPublisher(inbox=inbox)
        client = UserServiceHttpClient(
            settings=_settings(timeout_seconds=0.01),
            publisher=publisher,
            reply_inbox=inbox,
        )

        with pytest.raises(ExternalServiceError):
            await client.ensure_user_exists(user_id)

        assert inbox._futures == {}

    asyncio.run(scenario())


def test_get_user_by_email_publishes_lookup_request_and_returns_identity() -> None:
    async def scenario() -> None:
        user_id = uuid4()
        inbox = BrokerReplyInbox(service_name="project", instance_id="test-instance")
        publisher = ReplyingPublisher(
            inbox=inbox,
            responder=lambda topic, payload: {
                "correlation_id": payload["correlation_id"],
                "response_type": "user.email_lookup_provided",
                "email": payload["email"],
                "user_id": str(user_id),
                "exists": True,
            },
        )
        client = UserServiceHttpClient(
            settings=_settings(),
            publisher=publisher,
            reply_inbox=inbox,
        )

        identity = await client.get_user_by_email("invitee@example.com")

        assert identity.user_id == user_id
        assert identity.email == "invitee@example.com"
        assert publisher.events[0][0] == "user.email_lookup_requested"
        assert publisher.events[0][1]["reply_topic"] == inbox.reply_topic
        assert publisher.events[0][1]["email"] == "invitee@example.com"

    asyncio.run(scenario())


def test_get_user_by_email_raises_not_found_when_reply_reports_missing_user() -> None:
    async def scenario() -> None:
        inbox = BrokerReplyInbox(service_name="project", instance_id="test-instance")
        publisher = ReplyingPublisher(
            inbox=inbox,
            responder=lambda topic, payload: {
                "correlation_id": payload["correlation_id"],
                "response_type": "user.email_lookup_provided",
                "email": payload["email"],
                "user_id": None,
                "exists": False,
            },
        )
        client = UserServiceHttpClient(
            settings=_settings(),
            publisher=publisher,
            reply_inbox=inbox,
        )

        with pytest.raises(EntityNotFoundError):
            await client.get_user_by_email("missing@example.com")

    asyncio.run(scenario())


def test_resolve_ignores_duplicate_and_unknown_replies() -> None:
    async def scenario() -> None:
        inbox = BrokerReplyInbox(service_name="project", instance_id="test-instance")
        inbox.register("corr-1")
        assert inbox.resolve("corr-1", {"correlation_id": "corr-1"}) is True
        assert inbox.resolve("corr-1", {"correlation_id": "corr-1"}) is False
        await inbox.wait_for("corr-1", timeout=0.1)
        assert inbox.resolve("corr-1", {"correlation_id": "corr-1"}) is False
        assert inbox.resolve("unknown", {"correlation_id": "unknown"}) is False

    asyncio.run(scenario())


def test_reserve_user_time_publishes_participant_check_event() -> None:
    user_id = uuid4()
    project_id = uuid4()
    shift_id = uuid4()
    participant_id = uuid4()
    request_id = uuid4()
    publisher = FakePublisher()
    client = UserServiceHttpClient(
        settings=_settings(),
        publisher=publisher,
        reply_inbox=BrokerReplyInbox(service_name="project", instance_id="test-instance"),
    )
    time_from = datetime.now(tz=UTC)
    time_to = time_from + timedelta(hours=2)

    asyncio.run(
        client.reserve_user_time(
            request_id=request_id,
            user_id=user_id,
            time_from=time_from,
            time_to=time_to,
            project_id=project_id,
            shift_id=shift_id,
            entity_id=participant_id,
        )
    )

    assert publisher.events == [
        (
            "shift.participant_reservation_check_requested",
            {
                "request_id": str(request_id),
                "project_id": str(project_id),
                "shift_id": str(shift_id),
                "participant_id": str(participant_id),
                "user_id": str(user_id),
                "start_time": time_from.isoformat(),
                "end_time": time_to.isoformat(),
            },
        )
    ]


def test_ensure_user_resource_exists_checks_resource_kind_and_id() -> None:
    async def scenario() -> None:
        user_id = uuid4()
        resource_id = uuid4()
        client = StubResourceClient(
            [
                UserResourceItem(
                    resource_kind="cameras",
                    resource_id=resource_id,
                    title="Sony",
                    description="Camera",
                    resource_type="mirrorless",
                    size=None,
                    created_at=None,
                    windows=(),
                )
            ]
        )

        await client.ensure_user_resource_exists(
            user_id=user_id,
            resource_kind="cameras",
            resource_id=resource_id,
        )
        with pytest.raises(EntityNotFoundError):
            await client.ensure_user_resource_exists(
                user_id=user_id,
                resource_kind="lights",
                resource_id=resource_id,
            )

    asyncio.run(scenario())


def test_reserve_resource_time_publishes_resource_check_event() -> None:
    owner_user_id = uuid4()
    project_id = uuid4()
    shift_id = uuid4()
    resource_request_id = uuid4()
    resource_id = uuid4()
    request_id = uuid4()
    publisher = FakePublisher()
    client = UserServiceHttpClient(
        settings=_settings(),
        publisher=publisher,
        reply_inbox=BrokerReplyInbox(service_name="project", instance_id="test-instance"),
    )
    time_from = datetime.now(tz=UTC)
    time_to = time_from + timedelta(hours=1)

    asyncio.run(
        client.reserve_resource_time(
            request_id=request_id,
            owner_user_id=owner_user_id,
            resource_id=resource_id,
            time_from=time_from,
            time_to=time_to,
            project_id=project_id,
            shift_id=shift_id,
            entity_id=resource_request_id,
        )
    )

    assert publisher.events == [
        (
            "shift.resource_request_reservation_check_requested",
            {
                "request_id": str(request_id),
                "project_id": str(project_id),
                "shift_id": str(shift_id),
                "resource_request_id": str(resource_request_id),
                "owner_user_id": str(owner_user_id),
                "resource_id": str(resource_id),
                "start_time": time_from.isoformat(),
                "end_time": time_to.isoformat(),
            },
        )
    ]
