from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.application.commands.reservation_outbox import (
    build_participant_reservation_request_id,
    build_resource_reservation_request_id,
)
from app.application.ports.domain import (
    ProjectRepository,
    ResourceRequestRepository,
    ShiftParticipantRepository,
    ShiftRepository,
)
from app.application.support import require_participant, require_resource_request, require_shift
from app.domain.enums import ProjectRole, ResourceRequestStatus, ShiftParticipantStatus
from app.domain.errors.business import EntityNotFoundError


@dataclass(frozen=True, slots=True)
class GetParticipantApprovalStateQuery:
    participant_id: UUID


@dataclass(frozen=True, slots=True)
class ParticipantApprovalStateView:
    request_id: UUID
    project_id: UUID
    project_title: str
    shift_id: UUID
    shift_title: str
    participant_id: UUID
    user_id: UUID
    role_name: str
    time_from: datetime
    time_to: datetime
    status: int
    status_name: str
    user_reservation_id: UUID | None
    reserve_failure_reason: str | None


class GetParticipantApprovalStateHandler:
    def __init__(
        self,
        *,
        projects: ProjectRepository,
        shifts: ShiftRepository,
        shift_participants: ShiftParticipantRepository,
    ) -> None:
        self._projects = projects
        self._shifts = shifts
        self._shift_participants = shift_participants

    async def __call__(
        self,
        query: GetParticipantApprovalStateQuery,
    ) -> ParticipantApprovalStateView:
        participant = await require_participant(
            shift_participants=self._shift_participants,
            participant_id=query.participant_id,
        )
        shift = await require_shift(shifts=self._shifts, shift_id=participant.shift_id)
        project = await self._projects.get_by_id(shift.project_id)
        if project is None:
            raise EntityNotFoundError("Project is not found.")
        return ParticipantApprovalStateView(
            request_id=build_participant_reservation_request_id(participant.oid),
            project_id=project.oid,
            project_title=project.title,
            shift_id=shift.oid,
            shift_title=shift.title,
            participant_id=participant.oid,
            user_id=participant.user_id,
            role_name=_enum_name(participant.role, ProjectRole),
            time_from=participant.time_from,
            time_to=participant.time_to,
            status=int(participant.status),
            status_name=_enum_name(participant.status, ShiftParticipantStatus),
            user_reservation_id=participant.user_reservation_id,
            reserve_failure_reason=participant.reserve_failure_reason,
        )


@dataclass(frozen=True, slots=True)
class GetResourceApprovalStateQuery:
    resource_request_id: UUID


@dataclass(frozen=True, slots=True)
class ResourceApprovalStateView:
    request_id: UUID
    project_id: UUID
    project_title: str
    shift_id: UUID
    shift_title: str
    resource_request_id: UUID
    owner_user_id: UUID
    resource_id: UUID
    resource_type: str
    time_from: datetime
    time_to: datetime
    status: int
    status_name: str
    resource_reservation_id: UUID | None
    reserve_failure_reason: str | None


class GetResourceApprovalStateHandler:
    def __init__(
        self,
        *,
        projects: ProjectRepository,
        shifts: ShiftRepository,
        resource_requests: ResourceRequestRepository,
    ) -> None:
        self._projects = projects
        self._shifts = shifts
        self._resource_requests = resource_requests

    async def __call__(
        self,
        query: GetResourceApprovalStateQuery,
    ) -> ResourceApprovalStateView:
        request = await require_resource_request(
            resource_requests=self._resource_requests,
            request_id=query.resource_request_id,
        )
        shift = await require_shift(shifts=self._shifts, shift_id=request.shift_id)
        project = await self._projects.get_by_id(request.project_id)
        if project is None:
            raise EntityNotFoundError("Project is not found.")
        return ResourceApprovalStateView(
            request_id=build_resource_reservation_request_id(request.oid),
            project_id=project.oid,
            project_title=project.title,
            shift_id=shift.oid,
            shift_title=shift.title,
            resource_request_id=request.oid,
            owner_user_id=request.resource_owner_user_id,
            resource_id=request.resource_id,
            resource_type=request.resource_type,
            time_from=request.time_from,
            time_to=request.time_to,
            status=int(request.status),
            status_name=_enum_name(request.status, ResourceRequestStatus),
            resource_reservation_id=request.resource_reservation_id,
            reserve_failure_reason=request.reserve_failure_reason,
        )


def _enum_name(
    value: object,
    enum_cls: type[ProjectRole] | type[ShiftParticipantStatus] | type[ResourceRequestStatus],
) -> str:
    if hasattr(value, "name"):
        return str(getattr(value, "name"))
    return enum_cls(int(value)).name
