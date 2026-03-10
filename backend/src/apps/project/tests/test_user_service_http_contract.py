import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx

from app.config import UserService
from app.presentation.http.user_service import UserServiceHttpClient


def test_reserve_user_time_uses_common_availability_contract(monkeypatch) -> None:
    user_id = uuid4()
    request_id = uuid4()
    reservation_id = uuid4()
    captured: dict[str, object] = {}

    class FakeAsyncClient:
        def __init__(self, *, base_url: str, timeout: float) -> None:
            self._base_url = base_url.rstrip("/")
            self._timeout = timeout

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def request(
            self,
            *,
            method: str,
            url: str,
            json: dict | None = None,
            params: dict | None = None,
            headers: dict[str, str] | None = None,
        ) -> httpx.Response:
            del params, headers, self._timeout
            captured["method"] = method
            captured["url"] = url
            captured["json"] = json
            request = httpx.Request(method=method, url=f"{self._base_url}{url}")
            return httpx.Response(
                200,
                request=request,
                json={"reservation_id": str(reservation_id)},
            )

    monkeypatch.setattr(
        "app.presentation.http.user_service.httpx.AsyncClient",
        FakeAsyncClient,
    )

    settings = UserService(
        USER_SERVICE_BASE_URL="http://user.test",
        USER_SERVICE_TIMEOUT_SECONDS=1,
    )
    client = UserServiceHttpClient(settings=settings)
    time_from = datetime.now(tz=UTC)
    time_to = time_from + timedelta(hours=2)

    result = asyncio.run(
        client.reserve_user_time(
            request_id=request_id,
            user_id=user_id,
            time_from=time_from,
            time_to=time_to,
            project_id=uuid4(),
            shift_id=uuid4(),
            entity_id=uuid4(),
        )
    )

    assert result == reservation_id
    assert captured["method"] == "POST"
    assert captured["url"] == f"/users/{user_id}/availability/reserve"
    assert captured["json"] == {
        "request_id": str(request_id),
        "owner_id": str(user_id),
        "obj_id": str(user_id),
        "start_time": time_from.isoformat().replace("+00:00", "Z"),
        "end_time": time_to.isoformat().replace("+00:00", "Z"),
    }


def test_reserve_resource_time_uses_common_availability_contract(monkeypatch) -> None:
    owner_user_id = uuid4()
    resource_id = uuid4()
    request_id = uuid4()
    reservation_id = uuid4()
    captured: dict[str, object] = {}

    class FakeAsyncClient:
        def __init__(self, *, base_url: str, timeout: float) -> None:
            self._base_url = base_url.rstrip("/")
            self._timeout = timeout

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def request(
            self,
            *,
            method: str,
            url: str,
            json: dict | None = None,
            params: dict | None = None,
            headers: dict[str, str] | None = None,
        ) -> httpx.Response:
            del params, headers, self._timeout
            captured["method"] = method
            captured["url"] = url
            captured["json"] = json
            request = httpx.Request(method=method, url=f"{self._base_url}{url}")
            return httpx.Response(
                200,
                request=request,
                json={"reservation_id": str(reservation_id)},
            )

    monkeypatch.setattr(
        "app.presentation.http.user_service.httpx.AsyncClient",
        FakeAsyncClient,
    )

    settings = UserService(
        USER_SERVICE_BASE_URL="http://user.test",
        USER_SERVICE_TIMEOUT_SECONDS=1,
    )
    client = UserServiceHttpClient(settings=settings)
    time_from = datetime.now(tz=UTC)
    time_to = time_from + timedelta(hours=1)

    result = asyncio.run(
        client.reserve_resource_time(
            request_id=request_id,
            owner_user_id=owner_user_id,
            resource_id=resource_id,
            time_from=time_from,
            time_to=time_to,
            project_id=uuid4(),
            shift_id=uuid4(),
            entity_id=uuid4(),
        )
    )

    assert result == reservation_id
    assert captured["method"] == "POST"
    assert captured["url"] == f"/users/{owner_user_id}/availability/reserve"
    assert captured["json"] == {
        "request_id": str(request_id),
        "owner_id": str(owner_user_id),
        "obj_id": str(resource_id),
        "start_time": time_from.isoformat().replace("+00:00", "Z"),
        "end_time": time_to.isoformat().replace("+00:00", "Z"),
    }
