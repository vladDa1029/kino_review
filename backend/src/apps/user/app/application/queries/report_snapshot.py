from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.application.ports.repositories import (
    CameraRepository,
    CameraTripodRepository,
    DescriptionRepository,
    LightRepository,
    LightTripodRepository,
    MicrofonRepository,
    RequisiteRepository,
    SoundRepository,
    UserRepository,
)
from app.domain.entity.base import BaseId


@dataclass(frozen=True, slots=True)
class ShiftReportParticipantContext:
    participant_id: UUID
    user_id: UUID
    project_role: str
    shift_role: str
    time_from: object
    time_to: object


@dataclass(frozen=True, slots=True)
class ShiftReportResourceContext:
    resource_request_id: UUID
    resource_id: UUID
    owner_user_id: UUID
    resource_type: str
    time_from: object
    time_to: object


@dataclass(frozen=True, slots=True)
class ProvideShiftReportSnapshotQuery:
    report_id: UUID
    participants: tuple[ShiftReportParticipantContext, ...]
    resources: tuple[ShiftReportResourceContext, ...]


class _GenericRepository(Protocol):
    async def get(self, reference) -> object | None:
        raise NotImplementedError


class ProvideShiftReportSnapshotHandler:
    _RESOURCE_REPOSITORIES: dict[str, str] = {
        "microfon": "microfons",
        "microfons": "microfons",
        "camera": "cameras",
        "cameras": "cameras",
        "camera-tripod": "camera_tripods",
        "camera-tripods": "camera_tripods",
        "light": "lights",
        "lights": "lights",
        "light-tripod": "light_tripods",
        "light-tripods": "light_tripods",
        "sound": "sounds",
        "sounds": "sounds",
        "requisite": "requisites",
        "requisites": "requisites",
    }

    def __init__(
        self,
        *,
        users: UserRepository,
        descriptions: DescriptionRepository,
        microfons: MicrofonRepository,
        cameras: CameraRepository,
        camera_tripods: CameraTripodRepository,
        lights: LightRepository,
        light_tripods: LightTripodRepository,
        sounds: SoundRepository,
        requisites: RequisiteRepository,
    ) -> None:
        self._users = users
        self._descriptions = descriptions
        self._resource_repositories: dict[str, _GenericRepository] = {
            "microfons": microfons,
            "cameras": cameras,
            "camera_tripods": camera_tripods,
            "lights": lights,
            "light_tripods": light_tripods,
            "sounds": sounds,
            "requisites": requisites,
        }

    async def __call__(self, query: ProvideShiftReportSnapshotQuery) -> dict[str, list[dict[str, object | None]]]:
        user_ids = {
            context.user_id for context in query.participants
        } | {context.owner_user_id for context in query.resources}

        users_payload: list[dict[str, object | None]] = []
        for user_id in sorted(user_ids, key=str):
            user = await self._users.get(user_id)
            description = await self._descriptions.get_by_user_id(BaseId(user_id))
            users_payload.append(
                {
                    "user_id": user_id,
                    "username": description.username if description is not None else None,
                    "phone": str(description.phone) if description is not None else None,
                    "email": str(user.email) if user is not None else None,
                }
            )

        resources_payload: list[dict[str, object | None]] = []
        for context in query.resources:
            repository_key = self._RESOURCE_REPOSITORIES.get(context.resource_type.lower())
            resource = None
            if repository_key is not None:
                resource = await self._resource_repositories[repository_key].get(context.resource_id)
                if (
                    resource is not None
                    and hasattr(resource, "users_id")
                    and UUID(str(getattr(resource, "users_id"))) != context.owner_user_id
                ):
                    resource = None

            resources_payload.append(
                {
                    "resource_id": context.resource_id,
                    "owner_user_id": context.owner_user_id,
                    "title": getattr(resource, "title", None),
                    "resource_type": getattr(resource, "type", None),
                    "description": getattr(resource, "description", None),
                    "size": getattr(resource, "size", None),
                }
            )

        return {"users": users_payload, "resources": resources_payload}
