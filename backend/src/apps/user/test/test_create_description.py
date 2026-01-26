import asyncio
from uuid import uuid4

from app.application.commands.create_description import (
    CreateDescriptionCommand,
    CreateDescriptionHandler,
)
from app.domain.entity.base import BaseId
from app.domain.service.description_service import DescriptionService
from test.helpers import (
    FakeDescriptionRepository,
    FakeEntityRepository,
    FakeIdGenerator,
    FakeTransaction,
    make_user,
)


def test_create_description_handler_commits() -> None:
    user_id = BaseId(uuid4())
    user = make_user(user_id, is_active=True)
    desc_id = BaseId(uuid4())

    user_repo = FakeEntityRepository([user])
    desc_repo = FakeDescriptionRepository([])
    tx = FakeTransaction()
    id_gen = FakeIdGenerator(desc_id)
    handler = CreateDescriptionHandler(
        user_repository=user_repo,
        description_repository=desc_repo,
        transaction=tx,
        id_generator=id_gen,
        service=DescriptionService(),
    )

    command = CreateDescriptionCommand(
        user_id=user_id,
        username="user",
        phone="89001234567",
    )

    asyncio.run(handler(command))

    assert len(desc_repo.added) == 1
    created = desc_repo.added[0]
    assert created.oid == desc_id
    assert created.user_id == user_id
    assert created.username == command.username
    assert str(created.phone) == command.phone
    assert tx.commits == 1
    assert tx.rollbacks == 0
