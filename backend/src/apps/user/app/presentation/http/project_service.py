from datetime import datetime
from uuid import UUID

import httpx

from app.application.ports.approvals import (
    ParticipantApprovalState,
    ProjectApprovalStatePort,
    ResourceApprovalState,
)
from app.config import ProjectService
from app.domain.errors.base import ApplicationError


class ProjectApprovalStateError(ApplicationError):
    """Project approval state is unavailable."""


class ProjectApprovalStateHttpClient(ProjectApprovalStatePort):
    def __init__(self, settings: ProjectService) -> None:
        self._settings = settings

    async def get_participant_approval_state(
        self,
        *,
        participant_id: UUID,
    ) -> ParticipantApprovalState:
        payload = await self._request(
            f"/internal/participants/{participant_id}/approval-state",
        )
        return ParticipantApprovalState(
            request_id=UUID(payload["request_id"]),
            project_id=UUID(payload["project_id"]),
            project_title=str(payload["project_title"]),
            shift_id=UUID(payload["shift_id"]),
            shift_title=str(payload["shift_title"]),
            participant_id=UUID(payload["participant_id"]),
            user_id=UUID(payload["user_id"]),
            role=str(payload["role"]),
            time_from=_parse_datetime(payload["time_from"]),
            time_to=_parse_datetime(payload["time_to"]),
            status=int(payload["status"]),
            status_name=str(payload["status_name"]),
            user_reservation_id=_optional_uuid(payload.get("user_reservation_id")),
            reserve_failure_reason=_optional_str(payload.get("reserve_failure_reason")),
        )

    async def get_resource_approval_state(
        self,
        *,
        resource_request_id: UUID,
    ) -> ResourceApprovalState:
        payload = await self._request(
            f"/internal/resource-requests/{resource_request_id}/approval-state",
        )
        return ResourceApprovalState(
            request_id=UUID(payload["request_id"]),
            project_id=UUID(payload["project_id"]),
            project_title=str(payload["project_title"]),
            shift_id=UUID(payload["shift_id"]),
            shift_title=str(payload["shift_title"]),
            resource_request_id=UUID(payload["resource_request_id"]),
            owner_user_id=UUID(payload["owner_user_id"]),
            resource_id=UUID(payload["resource_id"]),
            resource_type=str(payload["resource_type"]),
            time_from=_parse_datetime(payload["time_from"]),
            time_to=_parse_datetime(payload["time_to"]),
            status=int(payload["status"]),
            status_name=str(payload["status_name"]),
            resource_reservation_id=_optional_uuid(payload.get("resource_reservation_id")),
            reserve_failure_reason=_optional_str(payload.get("reserve_failure_reason")),
        )

    async def _request(self, path: str) -> dict:
        try:
            async with httpx.AsyncClient(
                base_url=self._settings.base_url.rstrip("/"),
                timeout=self._settings.timeout_seconds,
            ) as client:
                response = await client.get(
                    path,
                    headers={"X-Internal-Api-Key": self._settings.internal_api_key},
                )
        except httpx.HTTPError as exc:
            raise ProjectApprovalStateError(f"Project-service call failed: {exc}") from exc

        if response.status_code == 404:
            raise ProjectApprovalStateError("Approval request was not found in project-service.")
        if response.status_code == 403:
            raise ProjectApprovalStateError("Project-service internal authorization failed.")
        if response.is_error:
            raise ProjectApprovalStateError(
                f"Project-service returned {response.status_code}: {response.text}"
            )
        return response.json()


def _parse_datetime(value: object):
    if not isinstance(value, str):
        raise ProjectApprovalStateError("Project-service returned invalid datetime payload.")
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ProjectApprovalStateError("Project-service returned invalid datetime payload.") from exc


def _optional_uuid(value: object) -> UUID | None:
    if value is None:
        return None
    return UUID(str(value))


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
