import asyncio
from datetime import datetime
from uuid import uuid4

from app.application.commands.add_image import AddImageCommand, AddImageHandler
from app.domain.entity.base import BaseId, Requisite
from app.domain.service.image_service import ImageService
from test.helpers import (
    FakeEntityRepository,
    FakeIdGenerator,
    FakeImageRepository,
    FakeTransaction,
    make_user,
)


def test_add_image_handler_commits() -> None:
    user_id = BaseId(uuid4())
    user = make_user(user_id, is_active=True)
    requisite_id = BaseId(uuid4())
    image_id = BaseId(uuid4())

    requisite = Requisite(
        oid=requisite_id,
        users_id=user_id,
        title="prop",
        description="desc",
        type="decor",
        size="m",
        create_at=datetime(2024, 1, 1, 10, 0, 0),
    )

    user_repo = FakeEntityRepository([user])
    requisite_repo = FakeEntityRepository([requisite])
    image_repo = FakeImageRepository([])
    tx = FakeTransaction()
    id_gen = FakeIdGenerator(image_id)

    handler = AddImageHandler(
        user_repository=user_repo,
        requisite_repository=requisite_repo,
        image_repository=image_repo,
        transaction=tx,
        id_generator=id_gen,
        service=ImageService(),
    )

    command = AddImageCommand(
        user_id=user_id,
        requisite_id=requisite_id,
        file="file.jpg",
        title="image",
        storage_key="key",
        bucket="bucket",
        mime_type="image/jpeg",
        size=123,
        description="desc",
    )

    asyncio.run(handler(command))

    assert len(image_repo.added) == 1
    created = image_repo.added[0]
    assert created.oid == image_id
    assert created.requisite_id == requisite_id
    assert created.file == command.file
    assert created.title == command.title
    assert created.storage_key == command.storage_key
    assert created.bucket == command.bucket
    assert created.mime_type == command.mime_type
    assert created.size == command.size
    assert created.description == command.description
    assert tx.commits == 1
    assert tx.rollbacks == 0
