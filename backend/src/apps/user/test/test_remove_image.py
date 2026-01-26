import asyncio
from datetime import datetime
from uuid import uuid4

from app.application.commands.remove_image import RemoveImageCommand, RemoveImageHandler
from app.domain.entity.base import BaseId, Image, Requisite
from app.domain.service.image_service import ImageService
from test.helpers import (
    FakeEntityRepository,
    FakeImageRepository,
    FakeTransaction,
    make_user,
)


def test_remove_image_handler_commits() -> None:
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

    image = Image(
        oid=image_id,
        requisite_id=requisite_id,
        file="file.jpg",
        title="image",
        storage_key="key",
        bucket="bucket",
        mime_type="image/jpeg",
        size=123,
        description="desc",
        create_at=datetime(2024, 1, 1, 10, 0, 0),
    )

    user_repo = FakeEntityRepository([user])
    requisite_repo = FakeEntityRepository([requisite])
    image_repo = FakeImageRepository([image])
    tx = FakeTransaction()

    handler = RemoveImageHandler(
        user_repository=user_repo,
        requisite_repository=requisite_repo,
        image_repository=image_repo,
        transaction=tx,
        service=ImageService(),
    )

    command = RemoveImageCommand(
        user_id=user_id,
        requisite_id=requisite_id,
        image_id=image_id,
    )

    asyncio.run(handler(command))

    assert image_repo.deleted == [image]
    assert tx.commits == 1
    assert tx.rollbacks == 0
