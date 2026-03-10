import asyncio
from datetime import datetime
from uuid import uuid4

from app.application.commands.reserve_availability import (
    ReserveAvailabilityCommand,
    ReserveAvailabilityHandler,
)
from app.domain.entity.base import AvailabilityReservation, BaseId, Spare_time
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


def test_reserve_availability_handler_commits() -> None:
    user_id = BaseId(uuid4())
    user = make_user(user_id, is_active=True)
    obj_id = BaseId(uuid4())
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
