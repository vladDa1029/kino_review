import asyncio
from datetime import datetime
from uuid import uuid4

from app.application.commands.add_spare_time import (
    AddSpareTimeCommand,
    AddSpareTimeHandler,
)
from app.domain.entity.base import BaseId
from app.domain.service.free_time_service import FreeTimeService
from test.helpers import (
    FakeEntityRepository,
    FakeIdGenerator,
    FakeSpareTimeRepository,
    FakeTransaction,
    make_user,
)


def test_add_spare_time_handler_commits() -> None:
    user_id = BaseId(uuid4())
    user = make_user(user_id, is_active=True)
    timing_id = BaseId(uuid4())

    user_repo = FakeEntityRepository([user])
    spare_time_repo = FakeSpareTimeRepository([])
    tx = FakeTransaction()
    id_gen = FakeIdGenerator(timing_id)
    handler = AddSpareTimeHandler(
        user_repository=user_repo,
        spare_time_repository=spare_time_repo,
        transaction=tx,
        id_generator=id_gen,
        service=FreeTimeService(),
    )

    command = AddSpareTimeCommand(
        user_id=user_id,
        start_time=datetime(2024, 1, 2, 10, 0, 0),
        end_time=datetime(2024, 1, 2, 12, 0, 0),
    )

    asyncio.run(handler(command))

    assert len(spare_time_repo.added) == 1
    created = spare_time_repo.added[0]
    assert created.oid == timing_id
    assert created.obj == user_id
    assert created.start_time == command.start_time
    assert created.end_time == command.end_time
    assert tx.commits == 1
    assert tx.rollbacks == 0
