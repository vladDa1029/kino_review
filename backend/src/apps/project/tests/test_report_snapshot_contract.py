import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.application.ports.reporting import (
    ShiftReportParticipantContext,
    ShiftReportResourceContext,
)
from app.config import UserService
from app.domain.errors.business import ExternalServiceError
from app.infrastructure.broker.request_reply import BrokerReplyInbox
from app.presentation.report_snapshot import (
    SHIFT_REPORT_SNAPSHOT_FAILED,
    SHIFT_REPORT_SNAPSHOT_PROVIDED,
    SHIFT_REPORT_SNAPSHOT_REQUESTED_TOPIC,
    ShiftReportSnapshotBrokerClient,
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


def _settings(timeout_seconds: float = 1.0) -> UserService:
    return UserService(
        USER_SERVICE_BASE_URL="http://user.test",
        USER_SERVICE_TIMEOUT_SECONDS=timeout_seconds,
    )


def _participant_context() -> tuple[ShiftReportParticipantContext, ...]:
    now = now_utc()
    return (
        ShiftReportParticipantContext(
            participant_id=uuid4(),
            user_id=uuid4(),
            project_role="ACTOR",
            shift_role="ACTOR",
            time_from=now,
            time_to=now + timedelta(hours=1),
        ),
    )


def _resource_context(owner_user_id) -> tuple[ShiftReportResourceContext, ...]:
    now = now_utc()
    return (
        ShiftReportResourceContext(
            resource_request_id=uuid4(),
            resource_id=uuid4(),
            owner_user_id=owner_user_id,
            resource_type="camera",
            time_from=now,
            time_to=now + timedelta(hours=1),
        ),
    )


def test_fetch_snapshot_publishes_request_and_returns_snapshot() -> None:
    async def scenario() -> None:
        participant = _participant_context()[0]
        resource = _resource_context(participant.user_id)[0]
        inbox = BrokerReplyInbox(service_name="project", instance_id="test-instance")

        def responder(topic: str, payload: dict) -> dict:
            return {
                "correlation_id": payload["correlation_id"],
                "response_type": SHIFT_REPORT_SNAPSHOT_PROVIDED,
                "report_id": payload["report_id"],
                "users": [
                    {
                        "user_id": payload["participants"][0]["user_id"],
                        "username": "Ivan",
                        "phone": "+79990001122",
                        "email": "ivan@example.com",
                    }
                ],
                "resources": [
                    {
                        "resource_id": payload["resources"][0]["resource_id"],
                        "owner_user_id": payload["resources"][0]["owner_user_id"],
                        "title": "Sony A7",
                        "resource_type": "mirrorless",
                        "description": "Main camera",
                        "size": None,
                    }
                ],
            }

        publisher = ReplyingPublisher(inbox=inbox, responder=responder)
        client = ShiftReportSnapshotBrokerClient(
            settings=_settings(),
            publisher=publisher,
            reply_inbox=inbox,
        )
        report_id = uuid4()

        snapshot = await client.fetch_snapshot(
            report_id=report_id,
            project_id=uuid4(),
            shift_id=uuid4(),
            participants=(participant,),
            resources=(resource,),
        )

        assert publisher.events[0][0] == SHIFT_REPORT_SNAPSHOT_REQUESTED_TOPIC
        assert publisher.events[0][1]["reply_topic"] == inbox.reply_topic
        assert publisher.events[0][1]["report_id"] == str(report_id)
        assert snapshot.users[0].username == "Ivan"
        assert snapshot.resources[0].title == "Sony A7"

    asyncio.run(scenario())


def test_fetch_snapshot_raises_external_error_on_failed_reply() -> None:
    async def scenario() -> None:
        participant = _participant_context()[0]
        resource = _resource_context(participant.user_id)[0]
        inbox = BrokerReplyInbox(service_name="project", instance_id="test-instance")
        publisher = ReplyingPublisher(
            inbox=inbox,
            responder=lambda topic, payload: {
                "correlation_id": payload["correlation_id"],
                "response_type": SHIFT_REPORT_SNAPSHOT_FAILED,
                "report_id": payload["report_id"],
                "reason": "snapshot unavailable",
            },
        )
        client = ShiftReportSnapshotBrokerClient(
            settings=_settings(),
            publisher=publisher,
            reply_inbox=inbox,
        )

        with pytest.raises(ExternalServiceError):
            await client.fetch_snapshot(
                report_id=uuid4(),
                project_id=uuid4(),
                shift_id=uuid4(),
                participants=(participant,),
                resources=(resource,),
            )

    asyncio.run(scenario())


def test_fetch_snapshot_raises_external_error_on_timeout_and_cleans_waiter() -> None:
    async def scenario() -> None:
        participant = _participant_context()[0]
        resource = _resource_context(participant.user_id)[0]
        inbox = BrokerReplyInbox(service_name="project", instance_id="test-instance")
        publisher = ReplyingPublisher(inbox=inbox)
        client = ShiftReportSnapshotBrokerClient(
            settings=_settings(timeout_seconds=0.01),
            publisher=publisher,
            reply_inbox=inbox,
        )

        with pytest.raises(ExternalServiceError):
            await client.fetch_snapshot(
                report_id=uuid4(),
                project_id=uuid4(),
                shift_id=uuid4(),
                participants=(participant,),
                resources=(resource,),
            )

        assert inbox._futures == {}

    asyncio.run(scenario())
