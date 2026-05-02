import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.config import ProjectService
from app.infrastructure.adapters.request_reply import BrokerReplyInbox
from app.presentation.http.project_service import (
    PARTICIPANT_APPROVAL_STATE_FAILED,
    PARTICIPANT_APPROVAL_STATE_PROVIDED,
    PARTICIPANT_APPROVAL_STATE_REQUESTED_TOPIC,
    RESOURCE_APPROVAL_STATE_PROVIDED,
    RESOURCE_APPROVAL_STATE_REQUESTED_TOPIC,
    ProjectApprovalStateBrokerClient,
    ProjectApprovalStateError,
)


def now_utc() -> datetime:
    return datetime.now(tz=UTC)


class ReplyingPublisher:
    def __init__(self, inbox: BrokerReplyInbox, responder=None) -> None:
        self.events: list[tuple[str, dict]] = []
        self._inbox = inbox
        self._responder = responder

    async def publish(self, topic: str, payload: dict) -> None:
        self.events.append((topic, payload))
        if self._responder is None:
            return
        reply = self._responder(topic, payload)
        if reply is not None:
            self._inbox.resolve(payload["correlation_id"], reply)


def _settings(timeout_seconds: float = 1.0) -> ProjectService:
    return ProjectService(PROJECT_SERVICE_TIMEOUT_SECONDS=timeout_seconds)


def test_get_participant_approval_state_publishes_request_and_returns_state() -> None:
    async def scenario() -> None:
        correlation = {}
        now = now_utc()
        inbox = BrokerReplyInbox(service_name="user", instance_id="test-instance")

        def responder(topic: str, payload: dict) -> dict:
            correlation["id"] = payload["correlation_id"]
            return {
                "correlation_id": payload["correlation_id"],
                "response_type": PARTICIPANT_APPROVAL_STATE_PROVIDED,
                "request_id": str(uuid4()),
                "project_id": str(uuid4()),
                "project_title": "Feature film",
                "shift_id": str(uuid4()),
                "shift_title": "Night shoot",
                "participant_id": payload["participant_id"],
                "user_id": str(uuid4()),
                "role": "ACTOR",
                "time_from": now.isoformat(),
                "time_to": (now + timedelta(hours=1)).isoformat(),
                "status": 15,
                "status_name": "RESERVING",
                "user_reservation_id": None,
                "reserve_failure_reason": None,
            }

        publisher = ReplyingPublisher(inbox=inbox, responder=responder)
        client = ProjectApprovalStateBrokerClient(
            settings=_settings(),
            publisher=publisher,
            reply_inbox=inbox,
        )
        participant_id = uuid4()

        state = await client.get_participant_approval_state(participant_id=participant_id)

        assert publisher.events[0][0] == PARTICIPANT_APPROVAL_STATE_REQUESTED_TOPIC
        assert publisher.events[0][1]["participant_id"] == str(participant_id)
        assert publisher.events[0][1]["reply_topic"] == inbox.reply_topic
        assert publisher.events[0][1]["correlation_id"] == correlation["id"]
        assert state.participant_id == participant_id
        assert state.status_name == "RESERVING"

    asyncio.run(scenario())


def test_get_participant_approval_state_raises_timeout_and_cleans_waiter() -> None:
    async def scenario() -> None:
        inbox = BrokerReplyInbox(service_name="user", instance_id="test-instance")
        publisher = ReplyingPublisher(inbox=inbox)
        client = ProjectApprovalStateBrokerClient(
            settings=_settings(timeout_seconds=0.01),
            publisher=publisher,
            reply_inbox=inbox,
        )

        with pytest.raises(ProjectApprovalStateError):
            await client.get_participant_approval_state(participant_id=uuid4())

        assert inbox._futures == {}

    asyncio.run(scenario())


def test_get_participant_approval_state_raises_failed_reply() -> None:
    async def scenario() -> None:
        inbox = BrokerReplyInbox(service_name="user", instance_id="test-instance")
        publisher = ReplyingPublisher(
            inbox=inbox,
            responder=lambda topic, payload: {
                "correlation_id": payload["correlation_id"],
                "response_type": PARTICIPANT_APPROVAL_STATE_FAILED,
                "participant_id": payload["participant_id"],
                "reason": "not found",
            },
        )
        client = ProjectApprovalStateBrokerClient(
            settings=_settings(),
            publisher=publisher,
            reply_inbox=inbox,
        )

        with pytest.raises(ProjectApprovalStateError):
            await client.get_participant_approval_state(participant_id=uuid4())

    asyncio.run(scenario())


def test_get_resource_approval_state_publishes_request_and_returns_state() -> None:
    async def scenario() -> None:
        now = now_utc()
        inbox = BrokerReplyInbox(service_name="user", instance_id="test-instance")

        def responder(topic: str, payload: dict) -> dict:
            return {
                "correlation_id": payload["correlation_id"],
                "response_type": RESOURCE_APPROVAL_STATE_PROVIDED,
                "request_id": str(uuid4()),
                "project_id": str(uuid4()),
                "project_title": "Feature film",
                "shift_id": str(uuid4()),
                "shift_title": "Night shoot",
                "resource_request_id": payload["resource_request_id"],
                "owner_user_id": str(uuid4()),
                "resource_id": str(uuid4()),
                "resource_type": "camera",
                "time_from": now.isoformat(),
                "time_to": (now + timedelta(hours=1)).isoformat(),
                "status": 15,
                "status_name": "RESERVING",
                "resource_reservation_id": None,
                "reserve_failure_reason": None,
            }

        publisher = ReplyingPublisher(inbox=inbox, responder=responder)
        client = ProjectApprovalStateBrokerClient(
            settings=_settings(),
            publisher=publisher,
            reply_inbox=inbox,
        )
        resource_request_id = uuid4()

        state = await client.get_resource_approval_state(
            resource_request_id=resource_request_id
        )

        assert publisher.events[0][0] == RESOURCE_APPROVAL_STATE_REQUESTED_TOPIC
        assert publisher.events[0][1]["resource_request_id"] == str(resource_request_id)
        assert publisher.events[0][1]["reply_topic"] == inbox.reply_topic
        assert state.resource_request_id == resource_request_id
        assert state.resource_type == "camera"
        assert state.status_name == "RESERVING"

    asyncio.run(scenario())


def test_reply_inbox_ignores_duplicate_and_unknown_replies() -> None:
    async def scenario() -> None:
        inbox = BrokerReplyInbox(service_name="user", instance_id="test-instance")
        inbox.register("corr-1")
        assert inbox.resolve("corr-1", {"correlation_id": "corr-1"}) is True
        assert inbox.resolve("corr-1", {"correlation_id": "corr-1"}) is False
        await inbox.wait_for("corr-1", timeout=0.1)
        assert inbox.resolve("corr-1", {"correlation_id": "corr-1"}) is False
        assert inbox.resolve("unknown", {"correlation_id": "unknown"}) is False

    asyncio.run(scenario())
