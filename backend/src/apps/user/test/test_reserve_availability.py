import asyncio
from datetime import datetime
from uuid import uuid4

import pytest

from app.application.commands.reserve_availability import (
    ReserveAvailabilityCommand,
    ReserveAvailabilityHandler,
)
from app.application.resource_ownership import ResourceOwnershipResolver
from app.domain.entity.base import AvailabilityReservation, BaseId, Camera, Spare_time
from app.domain.errors.policy import OwnershipError
from app.domain.policy.ownership import OwnershipPolicy
from app.domain.service.availability_service import AvailabilityService
from app.domain.value.status import AvailabilityStatus
from test.helpers import (
    FakeEntityRepository,
    FakeSpareTimeRepository,
    FakeTransaction,
    make_user,
)


class SequenceIdGenerator:
    def __init__(self, values):
        self._values = list(values)

    def __call__(self) -> BaseId:
        return self._values.pop(0)


def make_resource_ownership_resolver(**repositories) -> ResourceOwnershipResolver:
    empty = FakeEntityRepository()
    return ResourceOwnershipResolver(
        microfon_repository=repositories.get("microfon_repository", empty),
        camera_repository=repositories.get("camera_repository", empty),
        camera_tripod_repository=repositories.get("camera_tripod_repository", empty),
        light_repository=repositories.get("light_repository", empty),
        light_tripod_repository=repositories.get("light_tripod_repository", empty),
        sound_repository=repositories.get("sound_repository", empty),
        requisite_repository=repositories.get("requisite_repository", empty),
        ownership_policy=OwnershipPolicy(),
    )


def test_reserve_availability_handler_commits() -> None:
    user_id = BaseId(uuid4())
    user = make_user(user_id, is_active=True)
    obj_id = user_id
    owner_id = user_id
    reservation_id = BaseId(uuid4())
    free_before_id = BaseId(uuid4())
    free_after_id = BaseId(uuid4())

    free_window = Spare_time(
        oid=BaseId(uuid4()),
        obj=obj_id,
        start_time=datetime(2024, 1, 1, 10, 0, 0),
        end_time=datetime(2024, 1, 1, 14, 0, 0),
        status=AvailabilityStatus("free"),
    )

    user_repo = FakeEntityRepository([user])
    spare_time_repo = FakeSpareTimeRepository([free_window])
    reservation_repo = FakeEntityRepository()
    tx = FakeTransaction()
    id_gen = SequenceIdGenerator([reservation_id, free_before_id, free_after_id])

    handler = ReserveAvailabilityHandler(
        user_repository=user_repo,
        reservation_repository=reservation_repo,
        spare_time_repository=spare_time_repo,
        microfon_free_time_repository=FakeSpareTimeRepository(),
        camera_free_time_repository=FakeSpareTimeRepository(),
        camera_tripod_free_time_repository=FakeSpareTimeRepository(),
        light_free_time_repository=FakeSpareTimeRepository(),
        light_tripod_free_time_repository=FakeSpareTimeRepository(),
        sound_free_time_repository=FakeSpareTimeRepository(),
        requisite_free_time_repository=FakeSpareTimeRepository(),
        transaction=tx,
        id_generator=id_gen,
        resource_ownership=make_resource_ownership_resolver(),
        service=AvailabilityService(),
    )

    command = ReserveAvailabilityCommand(
        request_id=BaseId(uuid4()),
        user_id=user_id,
        owner_id=owner_id,
        obj_id=obj_id,
        start_time=datetime(2024, 1, 1, 11, 0, 0),
        end_time=datetime(2024, 1, 1, 12, 0, 0),
    )

    result = asyncio.run(handler(command))

    assert free_window in spare_time_repo.deleted
    assert len(spare_time_repo.added) == 3
    assert len(reservation_repo.added) == 1
    assert result == reservation_id
    assert tx.commits == 1
    assert tx.rollbacks == 0


def test_reserve_availability_handler_is_idempotent_by_request_id() -> None:
    user_id = BaseId(uuid4())
    request_id = BaseId(uuid4())
    reservation_id = BaseId(uuid4())
    command = ReserveAvailabilityCommand(
        request_id=request_id,
        user_id=user_id,
        owner_id=user_id,
        obj_id=user_id,
        start_time=datetime(2024, 1, 1, 11, 0, 0),
        end_time=datetime(2024, 1, 1, 12, 0, 0),
    )
    reservation_repo = FakeEntityRepository(
        [
            AvailabilityReservation(
                oid=request_id,
                user_id=user_id,
                obj_id=user_id,
                start_time=command.start_time,
                end_time=command.end_time,
                reservation_id=reservation_id,
                created_at=datetime(2024, 1, 1, 10, 0, 0),
            )
        ]
    )

    handler = ReserveAvailabilityHandler(
        user_repository=FakeEntityRepository([make_user(user_id, is_active=True)]),
        reservation_repository=reservation_repo,
        spare_time_repository=FakeSpareTimeRepository(),
        microfon_free_time_repository=FakeSpareTimeRepository(),
        camera_free_time_repository=FakeSpareTimeRepository(),
        camera_tripod_free_time_repository=FakeSpareTimeRepository(),
        light_free_time_repository=FakeSpareTimeRepository(),
        light_tripod_free_time_repository=FakeSpareTimeRepository(),
        sound_free_time_repository=FakeSpareTimeRepository(),
        requisite_free_time_repository=FakeSpareTimeRepository(),
        transaction=FakeTransaction(),
        id_generator=SequenceIdGenerator([]),
        resource_ownership=make_resource_ownership_resolver(),
        service=AvailabilityService(),
    )

    result = asyncio.run(handler(command))

    assert result == reservation_id


def test_reserve_availability_handler_uses_resource_free_time_repository() -> None:
    user_id = BaseId(uuid4())
    resource_id = BaseId(uuid4())
    request_id = BaseId(uuid4())
    reservation_id = BaseId(uuid4())
    free_before_id = BaseId(uuid4())
    free_after_id = BaseId(uuid4())

    camera_window = Spare_time(
        oid=BaseId(uuid4()),
        obj=resource_id,
        start_time=datetime(2024, 1, 1, 10, 0, 0),
        end_time=datetime(2024, 1, 1, 14, 0, 0),
        status=AvailabilityStatus("free"),
    )

    camera_free_time_repo = FakeSpareTimeRepository([camera_window])
    spare_time_repo = FakeSpareTimeRepository()

    handler = ReserveAvailabilityHandler(
        user_repository=FakeEntityRepository([make_user(user_id, is_active=True)]),
        reservation_repository=FakeEntityRepository(),
        spare_time_repository=spare_time_repo,
        microfon_free_time_repository=FakeSpareTimeRepository(),
        camera_free_time_repository=camera_free_time_repo,
        camera_tripod_free_time_repository=FakeSpareTimeRepository(),
        light_free_time_repository=FakeSpareTimeRepository(),
        light_tripod_free_time_repository=FakeSpareTimeRepository(),
        sound_free_time_repository=FakeSpareTimeRepository(),
        requisite_free_time_repository=FakeSpareTimeRepository(),
        transaction=FakeTransaction(),
        id_generator=SequenceIdGenerator([reservation_id, free_before_id, free_after_id]),
        resource_ownership=make_resource_ownership_resolver(
            camera_repository=FakeEntityRepository(
                [
                    Camera(
                        oid=resource_id,
                        users_id=user_id,
                        title="Sony",
                        description="Camera",
                        type="mirrorless",
                        create_at=datetime(2024, 1, 1, 9, 0, 0),
                    )
                ]
            )
        ),
        service=AvailabilityService(),
    )

    result = asyncio.run(
        handler(
            ReserveAvailabilityCommand(
                request_id=request_id,
                user_id=user_id,
                owner_id=user_id,
                obj_id=resource_id,
                start_time=datetime(2024, 1, 1, 11, 0, 0),
                end_time=datetime(2024, 1, 1, 12, 0, 0),
            )
        )
    )

    assert result == reservation_id
    assert camera_window in camera_free_time_repo.deleted
    assert len(camera_free_time_repo.added) == 3
    assert spare_time_repo.added == []


def test_reserve_availability_handler_rejects_resource_owned_by_another_user() -> None:
    user_id = BaseId(uuid4())
    other_user_id = BaseId(uuid4())
    resource_id = BaseId(uuid4())
    camera = Camera(
        oid=resource_id,
        users_id=other_user_id,
        title="Sony",
        description="Camera",
        type="mirrorless",
        create_at=datetime(2024, 1, 1, 9, 0, 0),
    )
    camera_window = Spare_time(
        oid=BaseId(uuid4()),
        obj=resource_id,
        start_time=datetime(2024, 1, 1, 10, 0, 0),
        end_time=datetime(2024, 1, 1, 14, 0, 0),
        status=AvailabilityStatus("free"),
    )
    tx = FakeTransaction()
    handler = ReserveAvailabilityHandler(
        user_repository=FakeEntityRepository([make_user(user_id, is_active=True)]),
        reservation_repository=FakeEntityRepository(),
        spare_time_repository=FakeSpareTimeRepository(),
        microfon_free_time_repository=FakeSpareTimeRepository(),
        camera_free_time_repository=FakeSpareTimeRepository([camera_window]),
        camera_tripod_free_time_repository=FakeSpareTimeRepository(),
        light_free_time_repository=FakeSpareTimeRepository(),
        light_tripod_free_time_repository=FakeSpareTimeRepository(),
        sound_free_time_repository=FakeSpareTimeRepository(),
        requisite_free_time_repository=FakeSpareTimeRepository(),
        transaction=tx,
        id_generator=SequenceIdGenerator([]),
        resource_ownership=make_resource_ownership_resolver(
            camera_repository=FakeEntityRepository([camera])
        ),
        service=AvailabilityService(),
    )

    command = ReserveAvailabilityCommand(
        request_id=BaseId(uuid4()),
        user_id=user_id,
        owner_id=user_id,
        obj_id=resource_id,
        start_time=datetime(2024, 1, 1, 11, 0, 0),
        end_time=datetime(2024, 1, 1, 12, 0, 0),
    )

    with pytest.raises(OwnershipError):
        asyncio.run(handler(command))

    assert tx.commits == 0
    assert tx.rollbacks == 0
