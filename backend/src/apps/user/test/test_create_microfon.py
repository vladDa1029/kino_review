import asyncio
from datetime import datetime
from uuid import uuid4

import pytest

from app.application.commands.create_microfon import (
    CreateMicrofonCommand,
    CreateMicrofonHandler,
)
from app.application.errors.errors import UserNotFoundError
from app.domain.entity.base import BaseId, User
from app.domain.errors.policy import UserInactiveError
from app.domain.service.equipment_service import EquipmentService
from app.domain.value.email import Email


class FakeUserRepository:
    def __init__(self, user: User | None) -> None:
        self._user = user

    async def get(self, reference):  # pragma: no cover - signature compatibility
        return self._user


class FakeMicrofonRepository:
    def __init__(self) -> None:
        self.added = None

    async def add(self, entity) -> None:
        self.added = entity


class FakeTransaction:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class FakeIdGenerator:
    def __init__(self, value: BaseId) -> None:
        self._value = value

    def __call__(self) -> BaseId:
        return self._value


def make_user(user_id: BaseId, is_active: bool = True) -> User:
    return User(
        oid=user_id,
        email=Email("user@example.com"),
        is_active=is_active,
        create_at=datetime(2024, 1, 1, 0, 0, 0),
    )


def test_create_microfon_commits_and_persists() -> None:
    user_id = BaseId(uuid4())
    user = make_user(user_id, is_active=True)
    microfon_id = BaseId(uuid4())

    user_repo = FakeUserRepository(user)
    microfon_repo = FakeMicrofonRepository()
    tx = FakeTransaction()
    id_gen = FakeIdGenerator(microfon_id)
    handler = CreateMicrofonHandler(
        user_repository=user_repo,
        microfon_repository=microfon_repo,
        transaction=tx,
        id_generator=id_gen,
        service=EquipmentService(),
    )

    command = CreateMicrofonCommand(
        user_id=user_id,
        title="mic",
        description="desc",
        type="shotgun",
    )

    now_before = datetime.now()
    asyncio.run(handler(command))
    now_after = datetime.now()

    assert microfon_repo.added is not None
    assert microfon_repo.added.oid == microfon_id
    assert microfon_repo.added.users_id == user_id
    assert microfon_repo.added.title == command.title
    assert microfon_repo.added.description == command.description
    assert microfon_repo.added.type == command.type
    assert now_before <= microfon_repo.added.create_at <= now_after
    assert tx.commits == 1
    assert tx.rollbacks == 0


def test_create_microfon_user_not_found() -> None:
    user_id = BaseId(uuid4())
    microfon_id = BaseId(uuid4())

    user_repo = FakeUserRepository(None)
    microfon_repo = FakeMicrofonRepository()
    tx = FakeTransaction()
    id_gen = FakeIdGenerator(microfon_id)
    handler = CreateMicrofonHandler(
        user_repository=user_repo,
        microfon_repository=microfon_repo,
        transaction=tx,
        id_generator=id_gen,
        service=EquipmentService(),
    )

    command = CreateMicrofonCommand(
        user_id=user_id,
        title="mic",
        description="desc",
        type="shotgun",
    )

    with pytest.raises(UserNotFoundError):
        asyncio.run(handler(command))

    assert tx.commits == 0
    assert tx.rollbacks == 0
    assert microfon_repo.added is None


def test_create_microfon_rolls_back_on_policy_error() -> None:
    user_id = BaseId(uuid4())
    user = make_user(user_id, is_active=False)
    microfon_id = BaseId(uuid4())

    user_repo = FakeUserRepository(user)
    microfon_repo = FakeMicrofonRepository()
    tx = FakeTransaction()
    id_gen = FakeIdGenerator(microfon_id)
    handler = CreateMicrofonHandler(
        user_repository=user_repo,
        microfon_repository=microfon_repo,
        transaction=tx,
        id_generator=id_gen,
        service=EquipmentService(),
    )

    command = CreateMicrofonCommand(
        user_id=user_id,
        title="mic",
        description="desc",
        type="shotgun",
    )

    with pytest.raises(UserInactiveError):
        asyncio.run(handler(command))

    assert tx.commits == 0
    assert tx.rollbacks == 1
    assert microfon_repo.added is None
