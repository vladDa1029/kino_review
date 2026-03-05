from datetime import datetime
from uuid import UUID

import httpx

from app.application.ports.domain import UserServicePort
from app.config import UserService
from app.domain.errors.business import EntityNotFoundError, ExternalServiceError


class UserServiceHttpClient(UserServicePort):
    def __init__(self, settings: UserService) -> None:
        self._settings = settings

    async def ensure_user_exists(self, user_id: UUID) -> None:
        data = await self._request("GET", f"/users/{user_id}")
        exists = data.get("exists", True)
        if not exists:
            raise EntityNotFoundError(f"User {user_id} does not exist.")

    async def reserve_user_time(
        self,
        *,
        user_id: UUID,
        time_from: datetime,
        time_to: datetime,
        project_id: UUID,
        shift_id: UUID,
        entity_id: UUID,
    ) -> UUID:
        data = await self._request(
            "POST",
            "/reservations/user-time",
            json={
                "user_id": str(user_id),
                "time_from": time_from.isoformat(),
                "time_to": time_to.isoformat(),
                "project_id": str(project_id),
                "shift_id": str(shift_id),
                "entity_id": str(entity_id),
                "source": "project-service",
                "entity_type": "shift_participant",
            },
        )
        reservation_id = data.get("reservation_id")
        if not reservation_id:
            raise ExternalServiceError("User-service did not return reservation_id.")
        return UUID(reservation_id)

    async def reserve_resource_time(
        self,
        *,
        owner_user_id: UUID,
        resource_id: UUID,
        time_from: datetime,
        time_to: datetime,
        project_id: UUID,
        shift_id: UUID,
        entity_id: UUID,
    ) -> UUID:
        data = await self._request(
            "POST",
            "/reservations/resource-time",
            json={
                "owner_user_id": str(owner_user_id),
                "resource_id": str(resource_id),
                "time_from": time_from.isoformat(),
                "time_to": time_to.isoformat(),
                "project_id": str(project_id),
                "shift_id": str(shift_id),
                "entity_id": str(entity_id),
                "source": "project-service",
                "entity_type": "resource_request",
            },
        )
        reservation_id = data.get("reservation_id")
        if not reservation_id:
            raise ExternalServiceError("User-service did not return reservation_id.")
        return UUID(reservation_id)

    async def _request(self, method: str, path: str, json: dict | None = None) -> dict:
        try:
            async with httpx.AsyncClient(
                base_url=self._settings.base_url.rstrip("/"),
                timeout=self._settings.timeout_seconds,
            ) as client:
                response = await client.request(method=method, url=path, json=json)
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
