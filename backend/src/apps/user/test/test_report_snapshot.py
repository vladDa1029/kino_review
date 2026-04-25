import asyncio
from dataclasses import dataclass
from uuid import UUID, uuid4

from app.application.queries.report_snapshot import (
    ProvideShiftReportSnapshotHandler,
    ProvideShiftReportSnapshotQuery,
    ShiftReportParticipantContext,
    ShiftReportResourceContext,
)
from app.domain.entity.base import BaseId


@dataclass
class FakeUser:
    oid: BaseId
    email: str


@dataclass
class FakeDescription:
    oid: BaseId
    user_id: BaseId
    username: str
    phone: str


@dataclass
class FakeResource:
    oid: UUID
    users_id: BaseId
    title: str
    description: str
    type: str
    size: str | None = None


class FakeUserRepo:
    def __init__(self) -> None:
        self.data: dict[UUID, FakeUser] = {}

    async def get(self, reference) -> FakeUser | None:
        return self.data.get(UUID(str(reference)))


class FakeDescriptionRepo:
    def __init__(self) -> None:
        self.data: dict[UUID, FakeDescription] = {}

    async def get_by_user_id(self, user_id) -> FakeDescription | None:
        return self.data.get(UUID(str(user_id)))


class FakeEquipmentRepo:
    def __init__(self) -> None:
        self.data: dict[UUID, FakeResource] = {}

    async def get(self, reference) -> FakeResource | None:
        return self.data.get(UUID(str(reference)))


def _build_handler(
    *,
    users: FakeUserRepo,
    descriptions: FakeDescriptionRepo,
    cameras: FakeEquipmentRepo,
) -> ProvideShiftReportSnapshotHandler:
    empty = FakeEquipmentRepo()
    return ProvideShiftReportSnapshotHandler(
        users=users,
        descriptions=descriptions,
        microfons=empty,
        cameras=cameras,
        camera_tripods=empty,
        lights=empty,
        light_tripods=empty,
        sounds=empty,
        requisites=empty,
    )


def test_report_snapshot_returns_user_and_resource_enrichment() -> None:
    async def scenario() -> None:
        users = FakeUserRepo()
        descriptions = FakeDescriptionRepo()
        cameras = FakeEquipmentRepo()
        user_id = uuid4()
        resource_id = uuid4()

        users.data[user_id] = FakeUser(oid=BaseId(user_id), email="ivan@example.com")
        descriptions.data[user_id] = FakeDescription(
            oid=BaseId(uuid4()),
            user_id=BaseId(user_id),
            username="Ivan Ivanov",
            phone="+79990001122",
        )
        cameras.data[resource_id] = FakeResource(
            oid=resource_id,
            users_id=BaseId(user_id),
            title="Sony A7",
            description="Main camera",
            type="mirrorless",
        )
        handler = _build_handler(users=users, descriptions=descriptions, cameras=cameras)

        payload = await handler(
            ProvideShiftReportSnapshotQuery(
                report_id=uuid4(),
                participants=(
                    ShiftReportParticipantContext(
                        participant_id=uuid4(),
                        user_id=user_id,
                        project_role="ACTOR",
                        shift_role="ACTOR",
                        time_from=object(),
                        time_to=object(),
                    ),
                ),
                resources=(
                    ShiftReportResourceContext(
                        resource_request_id=uuid4(),
                        resource_id=resource_id,
                        owner_user_id=user_id,
                        resource_type="camera",
                        time_from=object(),
                        time_to=object(),
                    ),
                ),
            )
        )

        assert payload["users"][0]["username"] == "Ivan Ivanov"
        assert payload["users"][0]["phone"] == "+79990001122"
        assert payload["users"][0]["email"] == "ivan@example.com"
        assert payload["resources"][0]["title"] == "Sony A7"
        assert payload["resources"][0]["resource_type"] == "mirrorless"

    asyncio.run(scenario())


def test_report_snapshot_returns_none_for_missing_fields() -> None:
    async def scenario() -> None:
        users = FakeUserRepo()
        descriptions = FakeDescriptionRepo()
        cameras = FakeEquipmentRepo()
        user_id = uuid4()
        resource_id = uuid4()

        handler = _build_handler(users=users, descriptions=descriptions, cameras=cameras)
        payload = await handler(
            ProvideShiftReportSnapshotQuery(
                report_id=uuid4(),
                participants=(
                    ShiftReportParticipantContext(
                        participant_id=uuid4(),
                        user_id=user_id,
                        project_role="ACTOR",
                        shift_role="ACTOR",
                        time_from=object(),
                        time_to=object(),
                    ),
                ),
                resources=(
                    ShiftReportResourceContext(
                        resource_request_id=uuid4(),
                        resource_id=resource_id,
                        owner_user_id=user_id,
                        resource_type="camera",
                        time_from=object(),
                        time_to=object(),
                    ),
                ),
            )
        )

        assert payload["users"][0]["username"] is None
        assert payload["users"][0]["phone"] is None
        assert payload["users"][0]["email"] is None
        assert payload["resources"][0]["title"] is None
        assert payload["resources"][0]["description"] is None

    asyncio.run(scenario())


def test_report_snapshot_ignores_resource_owned_by_another_user() -> None:
    async def scenario() -> None:
        users = FakeUserRepo()
        descriptions = FakeDescriptionRepo()
        cameras = FakeEquipmentRepo()
        owner_user_id = uuid4()
        actual_owner_id = uuid4()
        resource_id = uuid4()

        cameras.data[resource_id] = FakeResource(
            oid=resource_id,
            users_id=BaseId(actual_owner_id),
            title="Sony A7",
            description="Main camera",
            type="mirrorless",
        )
        handler = _build_handler(users=users, descriptions=descriptions, cameras=cameras)

        payload = await handler(
            ProvideShiftReportSnapshotQuery(
                report_id=uuid4(),
                participants=(),
                resources=(
                    ShiftReportResourceContext(
                        resource_request_id=uuid4(),
                        resource_id=resource_id,
                        owner_user_id=owner_user_id,
                        resource_type="camera",
                        time_from=object(),
                        time_to=object(),
                    ),
                ),
            )
        )

        assert payload["resources"][0]["title"] is None
        assert payload["resources"][0]["description"] is None

    asyncio.run(scenario())
