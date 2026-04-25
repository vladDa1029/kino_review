from dataclasses import dataclass
from uuid import UUID

from app.application.ports.broker import EventPublisher
from app.application.ports.domain import (
    ClockPort,
    ProjectRepository,
    ResourceRequestRepository,
    ShiftParticipantRepository,
    ShiftReportRepository,
    ShiftRepository,
)
from app.application.ports.transaction import TransactionManager
from app.application.reports_support import mark_shift_reports_stale
from app.application.support import publish_best_effort
from app.domain.enums import ProjectRole, ResourceRequestStatus, ShiftParticipantStatus
from app.domain.services import ResourceRequestService, ShiftParticipantService

PARTICIPANT_APPROVAL_REQUESTED_TOPIC = "shift.participant_approval_requested"
RESOURCE_APPROVAL_REQUESTED_TOPIC = "shift.resource_request_approval_requested"


@dataclass(frozen=True, slots=True, kw_only=True)
class HandleParticipantReservationCheckSucceededCommand:
    request_id: UUID
    project_id: UUID
    shift_id: UUID
    participant_id: UUID
    user_id: UUID


class HandleParticipantReservationCheckSucceededHandler:
    def __init__(
        self,
        *,
        publisher: EventPublisher,
        projects: ProjectRepository,
        shifts: ShiftRepository,
        shift_participants: ShiftParticipantRepository,
    ) -> None:
        self._publisher = publisher
        self._projects = projects
        self._shifts = shifts
        self._shift_participants = shift_participants

    async def __call__(
        self,
        command: HandleParticipantReservationCheckSucceededCommand,
    ) -> None:
        participant = await self._shift_participants.get_by_id(command.participant_id)
        if participant is None or _enum_name(participant.status, ShiftParticipantStatus) != "RESERVING":
            return
        shift = await self._shifts.get_by_id(participant.shift_id)
        project = await self._projects.get_by_id(command.project_id)
        await publish_best_effort(
            publisher=self._publisher,
            topic=PARTICIPANT_APPROVAL_REQUESTED_TOPIC,
            payload={
                "request_id": str(command.request_id),
                "project_id": str(command.project_id),
                "project_title": project.title if project is not None else "",
                "shift_id": str(command.shift_id),
                "shift_title": shift.title if shift is not None else "",
                "participant_id": str(command.participant_id),
                "user_id": str(command.user_id),
                "role": _enum_name(participant.role, ProjectRole),
                "time_from": participant.time_from.isoformat(),
                "time_to": participant.time_to.isoformat(),
            },
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class HandleParticipantReservationCheckFailedCommand:
    participant_id: UUID
    reason: str


class HandleParticipantReservationCheckFailedHandler:
    def __init__(
        self,
        *,
        transaction_manager: TransactionManager,
        clock: ClockPort,
        shift_participants: ShiftParticipantRepository,
        shift_reports: ShiftReportRepository,
        shift_participant_service: ShiftParticipantService,
    ) -> None:
        self._tx = transaction_manager
        self._clock = clock
        self._shift_participants = shift_participants
        self._shift_reports = shift_reports
        self._shift_participant_service = shift_participant_service

    async def __call__(self, command: HandleParticipantReservationCheckFailedCommand) -> None:
        participant = await self._shift_participants.get_by_id(command.participant_id)
        if participant is None or _enum_name(participant.status, ShiftParticipantStatus) != "RESERVING":
            return
        self._shift_participant_service.mark_reserve_failed(
            participant=participant,
            reason=command.reason,
            now=self._clock.now(),
        )
        await self._shift_participants.update(participant)
        await mark_shift_reports_stale(
            shift_reports=self._shift_reports,
            clock=self._clock,
            shift_id=participant.shift_id,
            reason="Participant status changed.",
        )
        await self._tx.commit()


@dataclass(frozen=True, slots=True, kw_only=True)
class HandleParticipantReservationSucceededCommand:
    project_id: UUID
    shift_id: UUID
    participant_id: UUID
    reservation_id: UUID


class HandleParticipantReservationSucceededHandler:
    def __init__(
        self,
        *,
        transaction_manager: TransactionManager,
        clock: ClockPort,
        publisher: EventPublisher,
        shift_participants: ShiftParticipantRepository,
        shift_reports: ShiftReportRepository,
        shift_participant_service: ShiftParticipantService,
    ) -> None:
        self._tx = transaction_manager
        self._clock = clock
        self._publisher = publisher
        self._shift_participants = shift_participants
        self._shift_reports = shift_reports
        self._shift_participant_service = shift_participant_service

    async def __call__(self, command: HandleParticipantReservationSucceededCommand) -> None:
        participant = await self._shift_participants.get_by_id(command.participant_id)
        if participant is None:
            return
        participant_status = _enum_name(participant.status, ShiftParticipantStatus)
        if participant_status == "RESERVED" and participant.user_reservation_id == command.reservation_id:
            return
        if participant_status != "RESERVING":
            return

        self._shift_participant_service.mark_reserved(
            participant=participant,
            reservation_id=command.reservation_id,
            now=self._clock.now(),
        )
        await self._shift_participants.update(participant)
        await mark_shift_reports_stale(
            shift_reports=self._shift_reports,
            clock=self._clock,
            shift_id=participant.shift_id,
            reason="Participant status changed.",
        )
        await self._tx.commit()
        await publish_best_effort(
            publisher=self._publisher,
            topic="shift.participant_reserved",
            payload={
                "project_id": str(command.project_id),
                "shift_id": str(command.shift_id),
                "participant_id": str(command.participant_id),
                "user_reservation_id": str(command.reservation_id),
            },
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class HandleParticipantReservationFailedCommand:
    participant_id: UUID
    reason: str


class HandleParticipantReservationFailedHandler:
    def __init__(
        self,
        *,
        transaction_manager: TransactionManager,
        clock: ClockPort,
        shift_participants: ShiftParticipantRepository,
        shift_reports: ShiftReportRepository,
        shift_participant_service: ShiftParticipantService,
    ) -> None:
        self._tx = transaction_manager
        self._clock = clock
        self._shift_participants = shift_participants
        self._shift_reports = shift_reports
        self._shift_participant_service = shift_participant_service

    async def __call__(self, command: HandleParticipantReservationFailedCommand) -> None:
        participant = await self._shift_participants.get_by_id(command.participant_id)
        if participant is None or _enum_name(participant.status, ShiftParticipantStatus) != "RESERVING":
            return
        self._shift_participant_service.mark_reserve_failed(
            participant=participant,
            reason=command.reason,
            now=self._clock.now(),
        )
        await self._shift_participants.update(participant)
        await mark_shift_reports_stale(
            shift_reports=self._shift_reports,
            clock=self._clock,
            shift_id=participant.shift_id,
            reason="Participant status changed.",
        )
        await self._tx.commit()


@dataclass(frozen=True, slots=True, kw_only=True)
class HandleResourceReservationCheckSucceededCommand:
    request_id: UUID
    project_id: UUID
    shift_id: UUID
    resource_request_id: UUID
    owner_user_id: UUID
    resource_id: UUID


class HandleResourceReservationCheckSucceededHandler:
    def __init__(
        self,
        *,
        publisher: EventPublisher,
        projects: ProjectRepository,
        shifts: ShiftRepository,
        resource_requests: ResourceRequestRepository,
    ) -> None:
        self._publisher = publisher
        self._projects = projects
        self._shifts = shifts
        self._resource_requests = resource_requests

    async def __call__(
        self,
        command: HandleResourceReservationCheckSucceededCommand,
    ) -> None:
        request = await self._resource_requests.get_by_id(command.resource_request_id)
        if request is None or _enum_name(request.status, ResourceRequestStatus) != "RESERVING":
            return
        shift = await self._shifts.get_by_id(request.shift_id)
        project = await self._projects.get_by_id(request.project_id)
        await publish_best_effort(
            publisher=self._publisher,
            topic=RESOURCE_APPROVAL_REQUESTED_TOPIC,
            payload={
                "request_id": str(command.request_id),
                "project_id": str(command.project_id),
                "project_title": project.title if project is not None else "",
                "shift_id": str(command.shift_id),
                "shift_title": shift.title if shift is not None else "",
                "resource_request_id": str(command.resource_request_id),
                "owner_user_id": str(command.owner_user_id),
                "resource_id": str(command.resource_id),
                "resource_type": request.resource_type,
                "time_from": request.time_from.isoformat(),
                "time_to": request.time_to.isoformat(),
            },
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class HandleResourceReservationCheckFailedCommand:
    resource_request_id: UUID
    reason: str


class HandleResourceReservationCheckFailedHandler:
    def __init__(
        self,
        *,
        transaction_manager: TransactionManager,
        clock: ClockPort,
        resource_requests: ResourceRequestRepository,
        shift_reports: ShiftReportRepository,
        resource_request_service: ResourceRequestService,
    ) -> None:
        self._tx = transaction_manager
        self._clock = clock
        self._resource_requests = resource_requests
        self._shift_reports = shift_reports
        self._resource_request_service = resource_request_service

    async def __call__(self, command: HandleResourceReservationCheckFailedCommand) -> None:
        request = await self._resource_requests.get_by_id(command.resource_request_id)
        if request is None or _enum_name(request.status, ResourceRequestStatus) != "RESERVING":
            return
        self._resource_request_service.mark_reserve_failed(
            request=request,
            reason=command.reason,
            now=self._clock.now(),
        )
        await self._resource_requests.update(request)
        await mark_shift_reports_stale(
            shift_reports=self._shift_reports,
            clock=self._clock,
            shift_id=request.shift_id,
            reason="Resource request status changed.",
        )
        await self._tx.commit()


@dataclass(frozen=True, slots=True, kw_only=True)
class HandleResourceReservationSucceededCommand:
    project_id: UUID
    shift_id: UUID
    resource_request_id: UUID
    reservation_id: UUID


class HandleResourceReservationSucceededHandler:
    def __init__(
        self,
        *,
        transaction_manager: TransactionManager,
        clock: ClockPort,
        publisher: EventPublisher,
        resource_requests: ResourceRequestRepository,
        shift_reports: ShiftReportRepository,
        resource_request_service: ResourceRequestService,
    ) -> None:
        self._tx = transaction_manager
        self._clock = clock
        self._publisher = publisher
        self._resource_requests = resource_requests
        self._shift_reports = shift_reports
        self._resource_request_service = resource_request_service

    async def __call__(self, command: HandleResourceReservationSucceededCommand) -> None:
        request = await self._resource_requests.get_by_id(command.resource_request_id)
        if request is None:
            return
        request_status = _enum_name(request.status, ResourceRequestStatus)
        if (
            request_status == "RESERVED"
            and request.resource_reservation_id == command.reservation_id
        ):
            return
        if request_status != "RESERVING":
            return

        self._resource_request_service.mark_reserved(
            request=request,
            reservation_id=command.reservation_id,
            now=self._clock.now(),
        )
        await self._resource_requests.update(request)
        await mark_shift_reports_stale(
            shift_reports=self._shift_reports,
            clock=self._clock,
            shift_id=request.shift_id,
            reason="Resource request status changed.",
        )
        await self._tx.commit()
        await publish_best_effort(
            publisher=self._publisher,
            topic="shift.resource_request_reserved",
            payload={
                "project_id": str(command.project_id),
                "shift_id": str(command.shift_id),
                "request_id": str(command.resource_request_id),
                "resource_reservation_id": str(command.reservation_id),
            },
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class HandleResourceReservationFailedCommand:
    resource_request_id: UUID
    reason: str


class HandleResourceReservationFailedHandler:
    def __init__(
        self,
        *,
        transaction_manager: TransactionManager,
        clock: ClockPort,
        resource_requests: ResourceRequestRepository,
        shift_reports: ShiftReportRepository,
        resource_request_service: ResourceRequestService,
    ) -> None:
        self._tx = transaction_manager
        self._clock = clock
        self._resource_requests = resource_requests
        self._shift_reports = shift_reports
        self._resource_request_service = resource_request_service

    async def __call__(self, command: HandleResourceReservationFailedCommand) -> None:
        request = await self._resource_requests.get_by_id(command.resource_request_id)
        if request is None or _enum_name(request.status, ResourceRequestStatus) != "RESERVING":
            return
        self._resource_request_service.mark_reserve_failed(
            request=request,
            reason=command.reason,
            now=self._clock.now(),
        )
        await self._resource_requests.update(request)
        await mark_shift_reports_stale(
            shift_reports=self._shift_reports,
            clock=self._clock,
            shift_id=request.shift_id,
            reason="Resource request status changed.",
        )
        await self._tx.commit()


def _enum_name(
    value: object,
    enum_cls: type[ShiftParticipantStatus] | type[ResourceRequestStatus] | type[ProjectRole],
) -> str:
    if hasattr(value, "name"):
        return str(getattr(value, "name"))
    return enum_cls(int(value)).name
