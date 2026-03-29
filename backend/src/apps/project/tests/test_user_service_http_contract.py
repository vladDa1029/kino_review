import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.config import UserService
from app.presentation.http.user_service import UserServiceHttpClient


class FakePublisher:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, topic: str, payload: dict) -> None:
        self.events.append((topic, payload))


def test_reserve_user_time_publishes_participant_check_event() -> None:
    user_id = uuid4()
    project_id = uuid4()
    shift_id = uuid4()
    participant_id = uuid4()
    request_id = uuid4()
    publisher = FakePublisher()
    settings = UserService(
        USER_SERVICE_BASE_URL="http://user.test",
        USER_SERVICE_TIMEOUT_SECONDS=1,
    )
    client = UserServiceHttpClient(settings=settings, publisher=publisher)
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


def test_reserve_resource_time_publishes_resource_check_event() -> None:
    owner_user_id = uuid4()
    project_id = uuid4()
    shift_id = uuid4()
    resource_request_id = uuid4()
    resource_id = uuid4()
    request_id = uuid4()
    publisher = FakePublisher()
    settings = UserService(
        USER_SERVICE_BASE_URL="http://user.test",
        USER_SERVICE_TIMEOUT_SECONDS=1,
    )
    client = UserServiceHttpClient(settings=settings, publisher=publisher)
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
