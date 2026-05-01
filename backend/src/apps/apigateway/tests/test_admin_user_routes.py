import asyncio
import importlib
import sys
import types
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import fastapi
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.application.errors import AccessDeniedError
from app.presentation.api.v1.routes.docs import router as docs_router


class _FromDishka:
    def __class_getitem__(cls, item):
        return cls


class _NoOpRouter:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def get(self, *args, **kwargs):
        def decorator(func):
            return func

        return decorator

    def api_route(self, *args, **kwargs):
        def decorator(func):
            return func

        return decorator


dishka_module = types.ModuleType("dishka")
dishka_module.FromDishka = _FromDishka
sys.modules.setdefault("dishka", dishka_module)

dishka_fastapi_module = types.ModuleType("dishka.integrations.fastapi")
dishka_fastapi_module.DishkaRoute = object
sys.modules.setdefault("dishka.integrations.fastapi", dishka_fastapi_module)

_original_api_router = fastapi.APIRouter
fastapi.APIRouter = _NoOpRouter
users_module = importlib.import_module("app.presentation.api.v1.routes.users")
fastapi.APIRouter = _original_api_router

_apply_admin_headers = users_module._apply_admin_headers
proxy_admin_users = users_module.proxy_admin_users


def test_docs_hub_contains_admin_user_swagger_link() -> None:
    app = FastAPI()
    app.include_router(docs_router)
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert 'href="/admin/user/docs"' in response.text


def test_apply_admin_headers_removes_spoofed_superuser_header() -> None:
    request = _build_request(
        path="/admin/user/users/target-user",
        headers=[(b"x-user-is-superuser", b"spoofed")],
    )
    request.state.user_headers = {
        "x-user-id": "admin-user",
        "x-user-token-type": "access",
        "x-user-is-superuser": "true",
    }

    headers = {"x-user-is-superuser": "spoofed"}

    _apply_admin_headers(headers, request, "users/target-user")

    assert headers == {
        "x-user-id": "target-user",
        "x-user-token-type": "access",
    }


def test_proxy_admin_users_rejects_non_admin_before_proxy_call() -> None:
    request = _build_request(path="/admin/user/users/target-user")
    request.state.user_payload = {
        "sub": "regular-user",
        "type": "access",
        "is_superuser": False,
    }
    request.state.user_headers = {
        "x-user-id": "regular-user",
        "x-user-token-type": "access",
        "x-user-is-superuser": "false",
    }
    client = SimpleNamespace(request=AsyncMock())
    services = SimpleNamespace(user="user:8002")

    with pytest.raises(AccessDeniedError, match="Admin access required."):
        asyncio.run(
            proxy_admin_users(
                request=request,
                path="users/target-user",
                ser=services,
                client=client,
            )
        )

    client.request.assert_not_called()


def _build_request(
    *,
    path: str,
    headers: list[tuple[bytes, bytes]] | None = None,
) -> Request:
    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": headers or [],
        "query_string": b"",
    }
    return Request(scope, receive)
