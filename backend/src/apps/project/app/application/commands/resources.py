from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.application.commands.reservation_outbox import (
    OUTBOX_STATUS_PENDING,
    ProcessReservationOutboxHandler,
    RESOURCE_RESERVE_OPERATION,
    build_resource_reservation_request_id,
)
from app.application.ports.broker import EventPublisher
from app.application.ports.domain import (
    ClockPort,
    IdGeneratorPort,
    ProjectMemberRepository,
    ReservationOutboxRepository,
    ResourceRequestRepository,
    ShiftRepository,
    UserServicePort,
)
from app.application.ports.transaction import TransactionManager
from app.application.support import (
    get_actor_member,
    publish_best_effort,
    require_resource_request,
    require_shift,
)
from app.domain.entities import ReservationOutboxMessage, ShiftResourceRequest
from app.domain.errors.business import ExternalServiceError
from app.domain.services import ResourceRequestService


@dataclass(frozen=True, slots=True, kw_only=True)
class CreateResourceRequestCommand:
    shift_id: UUID
    actor_user_id: UUID
    resource_type: str
    resource_id: UUID
    resource_owner_user_id: UUID
    time_from: datetime
    time_to: datetime


class CreateResourceRequestHandler:
    def __init__(
        self,
        *,
        transaction_manager: TransactionManager,
        clock: ClockPort,
        id_generator: IdGeneratorPort,
        publisher: EventPublisher,
        project_members: ProjectMemberRepository,
        shifts: ShiftRepository,
        resource_requests: ResourceRequestRepository,
        resource_request_service: ResourceRequestService,
    ) -> None:
        self._tx = transaction_manager
        self._clock = clock
        self._id_generator = id_generator
        self._publisher = publisher
        self._project_members = project_members
        self._shifts = shifts
        self._resource_requests = resource_requests
        self._resource_request_service = resource_request_service

    async def __call__(self, command: CreateResourceRequestCommand) -> ShiftResourceRequest:
        now = self._clock.now()
        try:
            shift = await require_shift(shifts=self._shifts, shift_id=command.shift_id)
            actor = await get_actor_member(
                project_members=self._project_members,
                project_id=shift.project_id,
                user_id=command.actor_user_id,
            )
            request = self._resource_request_service.create(
                actor=actor,
                request_id=self._id_generator(),
                shift=shift,
                resource_type=command.resource_type,
                resource_id=command.resource_id,
                resource_owner_user_id=command.resource_owner_user_id,
                time_from=command.time_from,
                time_to=command.time_to,
                now=now,
            )
            await self._resource_requests.add(request)
            await self._tx.commit()
        except Exception:
            await self._tx.rollback()
            raise

        await publish_best_effort(
            publisher=self._publisher,
            topic="shift.resource_request_created",
            payload={
                "project_id": str(shift.project_id),
                "shift_id": str(shift.oid),
                "request_id": str(request.oid),
                "resource_owner_user_id": str(command.resource_owner_user_id),
            },
        )
        return request


@dataclass(frozen=True, slots=True, kw_only=True)
class ApproveResourceRequestCommand:
    request_id: UUID
    actor_user_id: UUID


class ApproveResourceRequestHandler:
    def __init__(
        self,
        *,
        transaction_manager: TransactionManager,
        clock: ClockPort,
        publisher: EventPublisher,
        user_service: UserServicePort,
        reservation_outbox: ReservationOutboxRepository,
        reservation_processor: ProcessReservationOutboxHandler,
        resource_requests: ResourceRequestRepository,
        resource_request_service: ResourceRequestService,
    ) -> None:
        self._tx = transaction_manager
        self._clock = clock
        self._publisher = publisher
        self._user_service = user_service
        self._reservation_outbox = reservation_outbox
        self._reservation_processor = reservation_processor
        self._resource_requests = resource_requests
        self._resource_request_service = resource_request_service

    async def __call__(self, command: ApproveResourceRequestCommand) -> ShiftResourceRequest:
        now = self._clock.now()
        request = await require_resource_request(
            resource_requests=self._resource_requests,
            request_id=command.request_id,
        )
        request_key = build_resource_reservation_request_id(request.oid)
        try:
            self._resource_request_service.approve(
                request=request,
                actor_user_id=command.actor_user_id,
                now=now,
            )
            self._resource_request_service.mark_reserving(request=request, now=now)
            await self._resource_requests.update(request)
            await self._reservation_outbox.add(
                ReservationOutboxMessage(
                    oid=request_key,
                    operation=RESOURCE_RESERVE_OPERATION,
                    aggregate_id=request.oid,
                    status=OUTBOX_STATUS_PENDING,
                    attempts=0,
                    created_at=now,
                    updated_at=now,
                )
            )
            await self._tx.commit()
        except Exception:
            await self._tx.rollback()
            raise

        result = await self._reservation_processor.process_message(request_key)
        request = await require_resource_request(
            resource_requests=self._resource_requests,
            request_id=command.request_id,
        )
        if result.status == "failed":
            raise ExternalServiceError(result.error or "Resource reservation failed.")
        return request


@dataclass(frozen=True, slots=True, kw_only=True)
class RejectResourceRequestCommand:
    request_id: UUID
    actor_user_id: UUID
    reason: str


class RejectResourceRequestHandler:
    def __init__(
        self,
        *,
        transaction_manager: TransactionManager,
        clock: ClockPort,
        publisher: EventPublisher,
        resource_requests: ResourceRequestRepository,
        resource_request_service: ResourceRequestService,
    ) -> None:
        self._tx = transaction_manager
        self._clock = clock
        self._publisher = publisher
        self._resource_requests = resource_requests
        self._resource_request_service = resource_request_service

    async def __call__(self, command: RejectResourceRequestCommand) -> ShiftResourceRequest:
        now = self._clock.now()
        try:
            request = await require_resource_request(
                resource_requests=self._resource_requests,
                request_id=command.request_id,
            )
            self._resource_request_service.reject(
                request=request,
                actor_user_id=command.actor_user_id,
                reason=command.reason,
                now=now,
            )
            await self._resource_requests.update(request)
            await self._tx.commit()
        except Exception:
            await self._tx.rollback()
            raise

        await publish_best_effort(
            publisher=self._publisher,
            topic="shift.resource_request_rejected",
            payload={
                "project_id": str(request.project_id),
                "shift_id": str(request.shift_id),
                "request_id": str(request.oid),
                "rejection_reason": request.rejection_reason,
            },
        )
        return request
