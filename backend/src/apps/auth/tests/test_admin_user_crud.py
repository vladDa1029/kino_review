import asyncio
from uuid import uuid4

import pytest
from fastapi.routing import APIRoute

from app.application.errors.errors import AdminBlockedError, UserNotFoundError
from app.application.use_case.user_uc import AdminUserService
from app.domain.entities import User
from app.domain.values import Email
from app.presentations.api import router


class FakeTransactionManager:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        return None


class FakePasswordHasher:
    def hash_password(self, password: str) -> str:
        return f"hashed::{password}"


class FakeRepository:
    def __init__(self, users: list[User] | None = None) -> None:
        self.users = {user.oid: user for user in users or []}

    async def add(self, entity: User):
        self.users[entity.oid] = entity

    async def get(self, reference):
        return self.users.get(reference)

    async def get_by_email(self, email):
        return next(
            (user for user in self.users.values() if user.email.value == email.value),
            None,
        )

    async def get_by_username(self, username: str):
        return None

    async def list(self, filters=None, sorting=None, pagination=None):
        return list(self.users.values())

    async def delete(self, entity: User) -> None:
        self.users.pop(entity.oid, None)

    async def count(self, filters=None) -> int:
        return len(self.users)


def build_service(*users: User) -> tuple[AdminUserService, FakeTransactionManager]:
    tm = FakeTransactionManager()
    service = AdminUserService(
        transaction_manager=tm,
        password_hasher=FakePasswordHasher(),
        user_repository=FakeRepository(list(users)),
        generation=lambda: uuid4(),
    )
    return service, tm


def test_admin_routes_use_admin_prefix_and_tag() -> None:
    admin_routes = [
        route
        for route in router.routes
        if isinstance(route, APIRoute) and "admin" in route.tags
    ]

    assert admin_routes
    assert all(route.path.startswith("/admin/") for route in admin_routes)
    assert {route.path for route in admin_routes} == {
        "/admin/users",
        "/admin/users/{user_id}",
    }


def test_public_routes_use_expected_swagger_tags() -> None:
    route_tags = {
        route.path: route.tags
        for route in router.routes
        if isinstance(route, APIRoute)
    }

    assert route_tags["/health"] == ["system"]
    assert route_tags["/register"] == ["user"]
    assert route_tags["/login"] == ["user"]
    assert route_tags["/refresh"] == ["user"]
    assert route_tags["/logout"] == ["user"]


def test_admin_service_updates_is_active_for_regular_user() -> None:
    user = User(
        oid=uuid4(),
        email=Email("user@example.com"),
        password="hashed::old",
        is_active=True,
        is_superuser=False,
    )
    service, tm = build_service(user)

    updated = asyncio.run(service.update_user(user.oid, is_active=False))

    assert updated.is_active is False
    assert tm.commits == 1


def test_admin_service_rejects_blocking_superuser() -> None:
    admin_user = User(
        oid=uuid4(),
        email=Email("admin@example.com"),
        password="hashed::old",
        is_active=True,
        is_superuser=True,
    )
    service, tm = build_service(admin_user)

    with pytest.raises(AdminBlockedError):
        asyncio.run(service.update_user(admin_user.oid, is_active=False))

    assert admin_user.is_active is True
    assert tm.commits == 0


def test_admin_service_rejects_creating_blocked_superuser() -> None:
    service, tm = build_service()

    with pytest.raises(AdminBlockedError):
        asyncio.run(
            service.create_user(
                "admin@example.com",
                "secret123",
                is_active=False,
                is_superuser=True,
            )
        )

    assert tm.commits == 0


def test_admin_service_returns_not_found_for_unknown_user() -> None:
    service, _ = build_service()

    with pytest.raises(UserNotFoundError):
        asyncio.run(service.get_user(uuid4()))
