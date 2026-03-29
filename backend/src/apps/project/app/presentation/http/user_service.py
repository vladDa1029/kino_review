import logging
from datetime import datetime
from uuid import UUID

import httpx

from app.application.ports.broker import EventPublisher
from app.application.ports.domain import (
    UserResourceItem,
    UserResourceTimeWindow,
    UserServicePort,
)
from app.config import UserService
from app.domain.errors.business import EntityNotFoundError, ExternalServiceError


class UserServiceHttpClient(UserServicePort):
    _RESOURCE_PAGE_SIZE = 100
    _RESOURCE_MAX_PAGES = 1000
    _RESOURCE_KIND_PATHS: dict[str, str] = {
        "microfons": "/users/{user_id}/microfons",
        "cameras": "/users/{user_id}/cameras",
        "camera-tripods": "/users/{user_id}/camera-tripods",
        "lights": "/users/{user_id}/lights",
        "light-tripods": "/users/{user_id}/light-tripods",
        "sounds": "/users/{user_id}/sounds",
        "requisites": "/users/{user_id}/requisites",
    }
    _RESOURCE_WINDOWS_PATHS: dict[str, str] = {
        "microfons": "/users/{user_id}/microfons/{resource_id}/free-times",
        "cameras": "/users/{user_id}/cameras/{resource_id}/free-times",
        "camera-tripods": "/users/{user_id}/camera-tripods/{resource_id}/free-times",
        "lights": "/users/{user_id}/lights/{resource_id}/free-times",
        "light-tripods": "/users/{user_id}/light-tripods/{resource_id}/free-times",
        "sounds": "/users/{user_id}/sounds/{resource_id}/free-times",
        "requisites": "/users/{user_id}/requisites/{resource_id}/free-times",
    }
    _log = logging.getLogger(__name__)

    def __init__(self, settings: UserService, publisher: EventPublisher) -> None:
        self._settings = settings
        self._publisher = publisher

    async def ensure_user_exists(self, user_id: UUID) -> None:
        data = await self._request(
            "GET",
            f"/users/{user_id}",
            headers={"X-User-Id": str(user_id)},
        )
        exists = data.get("exists", True)
        if not exists:
            raise EntityNotFoundError(f"User {user_id} does not exist.")

    async def list_user_resources(
        self,
        *,
        user_id: UUID,
        resource_kinds: tuple[str, ...],
    ) -> list[UserResourceItem]:
        resources: list[UserResourceItem] = []
        headers = {"X-User-Id": str(user_id)}
        for kind in resource_kinds:
            path_template = self._RESOURCE_KIND_PATHS.get(kind)
            if path_template is None:
                continue
            seen_resource_ids: set[str] = set()
            fully_loaded = False
            for page in range(1, self._RESOURCE_MAX_PAGES + 1):
                data = await self._request(
                    "GET",
                    path_template.format(user_id=user_id),
                    params={
                        "page": page,
                        "page_size": self._RESOURCE_PAGE_SIZE,
                    },
                    headers=headers,
                )
                items = data.get("items", [])
                if not isinstance(items, list) or not items:
                    fully_loaded = True
                    break

                for item in items:
                    resource_id = item.get("oid")
                    if not resource_id or resource_id in seen_resource_ids:
                        continue
                    seen_resource_ids.add(resource_id)
                    created_raw = item.get("create_at")
                    created_at = None
                    if isinstance(created_raw, str):
                        created_at = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
                    windows = await self._list_resource_windows(
                        user_id=user_id,
                        resource_kind=kind,
                        resource_id=resource_id,
                        headers=headers,
                    )
                    resources.append(
                        UserResourceItem(
                            resource_kind=kind,
                            resource_id=UUID(resource_id),
                            title=str(item.get("title", "")),
                            description=str(item.get("description", "")),
                            resource_type=item.get("type"),
                            size=item.get("size"),
                            created_at=created_at,
                            windows=tuple(windows),
                        )
                    )

                pages = data.get("pages")
                if isinstance(pages, int):
                    if page >= pages:
                        fully_loaded = True
                        break
                elif len(items) < self._RESOURCE_PAGE_SIZE:
                    fully_loaded = True
                    break
            if not fully_loaded:
                self._log.warning(
                    "resource.pagination.limit_reached",
                    extra={
                        "user_id": str(user_id),
                        "resource_kind": kind,
                        "max_pages": self._RESOURCE_MAX_PAGES,
                    },
                )
                raise ExternalServiceError(
                    f"User-service pagination limit exceeded for '{kind}' resources."
                )
        return resources

    async def reserve_user_time(
        self,
        *,
        request_id: UUID,
        user_id: UUID,
        time_from: datetime,
        time_to: datetime,
        project_id: UUID,
        shift_id: UUID,
        entity_id: UUID,
    ) -> None:
        await self._publisher.publish(
            "shift.participant_reservation_check_requested",
            {
                "request_id": str(request_id),
                "project_id": str(project_id),
                "shift_id": str(shift_id),
                "participant_id": str(entity_id),
                "user_id": str(user_id),
                "start_time": time_from.isoformat(),
                "end_time": time_to.isoformat(),
            },
        )

    async def reserve_resource_time(
        self,
        *,
        request_id: UUID,
        owner_user_id: UUID,
        resource_id: UUID,
        time_from: datetime,
        time_to: datetime,
        project_id: UUID,
        shift_id: UUID,
        entity_id: UUID,
    ) -> None:
        await self._publisher.publish(
            "shift.resource_request_reservation_check_requested",
            {
                "request_id": str(request_id),
                "project_id": str(project_id),
                "shift_id": str(shift_id),
                "resource_request_id": str(entity_id),
                "owner_user_id": str(owner_user_id),
                "resource_id": str(resource_id),
                "start_time": time_from.isoformat(),
                "end_time": time_to.isoformat(),
            },
        )

    async def _request(
        self,
        method: str,
        path: str,
        json: dict | None = None,
        params: dict | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict:
        try:
            async with httpx.AsyncClient(
                base_url=self._settings.base_url.rstrip("/"),
                timeout=self._settings.timeout_seconds,
            ) as client:
                response = await client.request(
                    method=method,
                    url=path,
                    json=json,
                    params=params,
                    headers=headers,
                )
        except httpx.HTTPError as exc:
            raise ExternalServiceError(f"User-service call failed: {exc}") from exc

        if response.status_code == 404:
            raise EntityNotFoundError("Requested entity was not found in user-service.")

        if response.is_error:
            raise ExternalServiceError(
                f"User-service returned {response.status_code}: {response.text}"
            )

        if not response.content:
            return {}
        return response.json()

    async def _list_resource_windows(
        self,
        *,
        user_id: UUID,
        resource_kind: str,
        resource_id: str,
        headers: dict[str, str],
    ) -> list[UserResourceTimeWindow]:
        windows_path_template = self._RESOURCE_WINDOWS_PATHS.get(resource_kind)
        if windows_path_template is None:
            return []
        data = await self._request(
            "GET",
            windows_path_template.format(user_id=user_id, resource_id=resource_id),
            headers=headers,
        )
        windows: list[UserResourceTimeWindow] = []
        for item in data.get("items", []):
            window_id = item.get("oid")
            start_time_raw = item.get("start_time")
            end_time_raw = item.get("end_time")
            if (
                not window_id
                or not isinstance(start_time_raw, str)
                or not isinstance(end_time_raw, str)
            ):
                continue
            windows.append(
                UserResourceTimeWindow(
                    window_id=UUID(window_id),
                    start_time=datetime.fromisoformat(start_time_raw.replace("Z", "+00:00")),
                    end_time=datetime.fromisoformat(end_time_raw.replace("Z", "+00:00")),
                    status=str(item.get("status", "")),
                )
            )
        return windows
