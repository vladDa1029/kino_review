import asyncio
from uuid import uuid4

from app.application.commands.update_description import (
    UpdateDescriptionCommand,
    UpdateDescriptionHandler,
)
from app.domain.entity.base import BaseId, Description
from app.domain.service.description_service import DescriptionService
from app.domain.value.phone import Phone
from test.helpers import (
    FakeDescriptionRepository,
    FakeEntityRepository,
    FakeTransaction,
    make_user,
)


def test_update_description_handler_commits() -> None:
    user_id = BaseId(uuid4())
    user = make_user(user_id, is_active=True)
    desc_id = BaseId(uuid4())

    description = Description(
        oid=desc_id,
        user_id=user_id,
        username="old",
        phone=Phone("89001234567"),
    )

    user_repo = FakeEntityRepository([user])
    desc_repo = FakeDescriptionRepository([description])
    tx = FakeTransaction()
    handler = UpdateDescriptionHandler(
        user_repository=user_repo,
        description_repository=desc_repo,
        transaction=tx,
        service=DescriptionService(),
    )

    command = UpdateDescriptionCommand(
        user_id=user_id,
        description_id=desc_id,
        username="new",
        phone="89001112233",
    )

    asyncio.run(handler(command))

    assert description.username == command.username
    assert str(description.phone) == command.phone
    assert tx.commits == 1
    assert tx.rollbacks == 0
