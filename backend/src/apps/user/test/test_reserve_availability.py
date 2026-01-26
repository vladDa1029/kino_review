import asyncio
from datetime import datetime
from uuid import uuid4

from app.application.commands.reserve_availability import (
    ReserveAvailabilityCommand,
    ReserveAvailabilityHandler,
)
from app.domain.entity.base import BaseId, Spare_time
from app.domain.service.availability_service import AvailabilityService
from app.domain.value.status import AvailabilityStatus
from test.helpers import FakeEntityRepository, FakeSpareTimeRepository, FakeTransaction, make_user


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

    free_window = Spare_time(
        oid=BaseId(uuid4()),
        obj=obj_id,
        start_time=datetime(2024, 1, 1, 10, 0, 0),
        end_time=datetime(2024, 1, 1, 14, 0, 0),
        status=AvailabilityStatus("free"),
    )

    user_repo = FakeEntityRepository([user])
    spare_time_repo = FakeSpareTimeRepository([free_window])
    tx = FakeTransaction()
    id_gen = SequenceIdGenerator([BaseId(uuid4()), BaseId(uuid4()), BaseId(uuid4())])

    handler = ReserveAvailabilityHandler(
        user_repository=user_repo,
        spare_time_repository=spare_time_repo,
        transaction=tx,
        id_generator=id_gen,
        service=AvailabilityService(),
    )

    command = ReserveAvailabilityCommand(
        user_id=user_id,
        owner_id=owner_id,
        obj_id=obj_id,
        start_time=datetime(2024, 1, 1, 11, 0, 0),
        end_time=datetime(2024, 1, 1, 12, 0, 0),
    )

    asyncio.run(handler(command))

    assert free_window in spare_time_repo.deleted
    assert len(spare_time_repo.added) == 3
    assert tx.commits == 1
    assert tx.rollbacks == 0
