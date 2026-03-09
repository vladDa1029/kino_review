from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.application.ports.broker import EventPublisher
from app.application.ports.domain import (
    ClockPort,
    IdGeneratorPort,
    ProjectMemberRepository,
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
from app.domain.entities import ShiftResourceRequest
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
        resource_requests: ResourceRequestRepository,
        resource_request_service: ResourceRequestService,
    ) -> None:
        self._tx = transaction_manager
        self._clock = clock
        self._publisher = publisher
        self._user_service = user_service
        self._resource_requests = resource_requests
        self._resource_request_service = resource_request_service

    async def __call__(self, command: ApproveResourceRequestCommand) -> ShiftResourceRequest:
        now = self._clock.now()
        request = await require_resource_request(
            resource_requests=self._resource_requests,
            request_id=command.request_id,
        )
        try:
            self._resource_request_service.approve(
                request=request,
                actor_user_id=command.actor_user_id,
                now=now,
            )
            self._resource_request_service.mark_reserving(request=request, now=now)
            await self._resource_requests.update(request)

            reservation_id = await self._user_service.reserve_resource_time(
                owner_user_id=request.resource_owner_user_id,
                resource_id=request.resource_id,
                time_from=request.time_from,
                time_to=request.time_to,
                project_id=request.project_id,
                shift_id=request.shift_id,
                entity_id=request.oid,
            )
            self._resource_request_service.mark_reserved(
                request=request,
                reservation_id=reservation_id,
                now=self._clock.now(),
            )
            await self._resource_requests.update(request)
            await self._tx.commit()
        except Exception as exc:
            failed_marked = await self._try_mark_reserve_failed(
                request=request,
                reason=str(exc),
            )
            if failed_marked:
                await self._tx.commit()
            else:
                await self._tx.rollback()
            raise

        await publish_best_effort(
            publisher=self._publisher,
            topic="shift.resource_request_reserved",
            payload={
                "project_id": str(request.project_id),
                "shift_id": str(request.shift_id),
                "request_id": str(request.oid),
                "resource_reservation_id": str(request.resource_reservation_id),
            },
        )
        return request

    async def _try_mark_reserve_failed(
        self,
        *,
        request: ShiftResourceRequest,
        reason: str,
    ) -> bool:
        try:
            self._resource_request_service.mark_reserve_failed(
                request=request,
                reason=reason,
                now=self._clock.now(),
            )
            await self._resource_requests.update(request)
            return True
        except Exception:
            return False


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
