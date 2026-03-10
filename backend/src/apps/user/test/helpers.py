from datetime import datetime
from uuid import uuid4

from app.domain.entity.base import BaseId, User
from app.domain.value.email import Email


class FakeTransaction:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class FakeIdGenerator:
    def __init__(self, value: BaseId | None = None) -> None:
        self._value = value or BaseId(uuid4())

    def __call__(self) -> BaseId:
        return self._value


class FakeEntityRepository:
    def __init__(self, items: list | None = None) -> None:
        self._items = {item.oid: item for item in (items or [])}
        self.added: list = []
        self.updated: list = []
        self.deleted: list = []

    async def add(self, entity) -> None:
        self._items[entity.oid] = entity
        self.added.append(entity)

    async def get(self, reference):
        return self._items.get(reference)

    async def update(self, entity) -> None:
        self._items[entity.oid] = entity
        self.updated.append(entity)

    async def delete(self, entity) -> None:
        self._items.pop(entity.oid, None)
        self.deleted.append(entity)


class FakeDescriptionRepository(FakeEntityRepository):
    async def get_by_user_id(self, user_id: BaseId):
        for item in self._items.values():
            if item.user_id == user_id:
                return item
        return None


class FakeSpareTimeRepository(FakeEntityRepository):
    def __init__(self, items: list | None = None) -> None:
        super().__init__(items)

    async def list_by_obj_id(self, obj_id: BaseId):
        return [item for item in self._items.values() if item.obj == obj_id]


class FakeImageRepository(FakeEntityRepository):
    async def list_by_requisite_id(self, requisite_id: BaseId):
        return [
            item for item in self._items.values() if item.requisite_id == requisite_id
        ]


def make_user(user_id: BaseId, is_active: bool = True) -> User:
    return User(
        oid=user_id,
        email=Email("user@example.com"),
        is_active=is_active,
        create_at=datetime(2024, 1, 1, 0, 0, 0),
    )
