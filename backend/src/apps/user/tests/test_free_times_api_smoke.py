import asyncio
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.routing import APIRoute

from app.domain.entity.base import BaseId
from app.presentation.api import get_user_exists, router, strict_user_id_from_header


class StubGetUserExistsHandler:
    async def __call__(self, query) -> bool:
        return True


def _find_route(path: str, method: str) -> APIRoute | None:
    for candidate in router.routes:
        if not isinstance(candidate, APIRoute):
            continue
        if candidate.path == path and method.upper() in candidate.methods:
            return candidate
    return None


@pytest.mark.parametrize(
    "path",
    [
        "/users/{user_id}/microfons/{microfon_id}/free-times",
        "/users/{user_id}/cameras/{camera_id}/free-times",
        "/users/{user_id}/camera-tripods/{camera_tripod_id}/free-times",
        "/users/{user_id}/lights/{light_id}/free-times",
        "/users/{user_id}/light-tripods/{light_tripod_id}/free-times",
        "/users/{user_id}/sounds/{sound_id}/free-times",
        "/users/{user_id}/requisites/{requisite_id}/free-times",
    ],
)
def test_get_free_times_routes_registered(path: str) -> None:
    route = _find_route(path, "GET")
    assert route is not None


def test_strict_user_id_header_validation() -> None:
    user_id = uuid4()
    assert strict_user_id_from_header(user_id=user_id, x_user_id=user_id) == BaseId(
        user_id
    )

    with pytest.raises(HTTPException) as exc:
        strict_user_id_from_header(user_id=user_id, x_user_id=uuid4())
    assert exc.value.status_code == 403


def test_get_user_exists_handler_smoke() -> None:
    user_id = uuid4()
    result = asyncio.run(
        get_user_exists(
            user_id=user_id,
            handler=StubGetUserExistsHandler(),
            _=BaseId(user_id),
        )
    )
    assert result["exists"] is True
    assert result["user_id"] == user_id
