from dataclasses import dataclass
from uuid import UUID, uuid5

from app.application.ports.broker import EventPublisher
from app.application.ports.domain import (
    ClockPort,
    ReservationOutboxRepository,
    ResourceRequestRepository,
    ShiftParticipantRepository,
    ShiftRepository,
    UserServicePort,
)
from app.application.ports.transaction import TransactionManager
from app.application.support import publish_best_effort
from app.domain.entities import ReservationOutboxMessage
from app.domain.services import ResourceRequestService, ShiftParticipantService

RESERVATION_OUTBOX_NAMESPACE = UUID("3d46f2ae-2d14-4edf-aeb8-b0e4f15f6f20")
PARTICIPANT_RESERVE_OPERATION = "participant_reserve"
RESOURCE_RESERVE_OPERATION = "resource_request_reserve"
OUTBOX_STATUS_PENDING = "pending"
OUTBOX_STATUS_COMPLETED = "completed"


def build_participant_reservation_request_id(participant_id: UUID) -> UUID:
    return uuid5(RESERVATION_OUTBOX_NAMESPACE, f"participant-reserve:{participant_id}")


def build_resource_reservation_request_id(request_id: UUID) -> UUID:
    return uuid5(RESERVATION_OUTBOX_NAMESPACE, f"resource-request-reserve:{request_id}")


@dataclass(frozen=True, slots=True)
class ProcessReservationOutboxResult:
    status: str
    error: str | None = None


class ProcessReservationOutboxHandler:
    def __init__(
        self,
        *,
        transaction_manager: TransactionManager,
        clock: ClockPort,
        publisher: EventPublisher,
        user_service: UserServicePort,
        shifts: ShiftRepository,
        shift_participants: ShiftParticipantRepository,
        resource_requests: ResourceRequestRepository,
        reservation_outbox: ReservationOutboxRepository,
        shift_participant_service: ShiftParticipantService,
        resource_request_service: ResourceRequestService,
    ) -> None:
        self._tx = transaction_manager
        self._clock = clock
        self._publisher = publisher
        self._user_service = user_service
        self._shifts = shifts
        self._shift_participants = shift_participants
        self._resource_requests = resource_requests
        self._reservation_outbox = reservation_outbox
        self._shift_participant_service = shift_participant_service
        self._resource_request_service = resource_request_service

    async def __call__(self, *, limit: int = 20) -> int:
        messages = await self._reservation_outbox.list_pending(limit=limit)
        processed = 0
        for message in messages:
            await self.process_message(message.oid)
            processed += 1
        return processed

    async def process_message(self, message_id: UUID) -> ProcessReservationOutboxResult:
        message = await self._reservation_outbox.get_by_id(message_id)
        if message is None or message.status == OUTBOX_STATUS_COMPLETED:
            return ProcessReservationOutboxResult(status="completed")

        if message.operation == PARTICIPANT_RESERVE_OPERATION:
            return await self._process_participant_reserve(message)
        if message.operation == RESOURCE_RESERVE_OPERATION:
            return await self._process_resource_reserve(message)

        message.status = OUTBOX_STATUS_COMPLETED
        message.attempts += 1
        message.last_error = f"Unsupported reservation outbox operation: {message.operation}"
        message.updated_at = self._clock.now()
        await self._reservation_outbox.update(message)
        await self._tx.commit()
        return ProcessReservationOutboxResult(status="failed", error=message.last_error)

    async def _process_participant_reserve(
        self,
        message: ReservationOutboxMessage,
    ) -> ProcessReservationOutboxResult:
        participant = await self._shift_participants.get_by_id(message.aggregate_id)
        if participant is None:
            return await self._complete_missing_message(message, "Shift participant is not found.")
        if participant.user_reservation_id is not None:
            return await self._complete_message(message)
        if participant.status.name != "RESERVING":
            return await self._complete_message(
                message,
                error=f"Shift participant is in non-reserving status: {participant.status.name}",
            )

        shift = await self._shifts.get_by_id(participant.shift_id)
        if shift is None:
            return await self._complete_missing_message(message, "Shift is not found.")

        try:
            reservation_id = await self._user_service.reserve_user_time(
                request_id=message.oid,
                user_id=participant.user_id,
                time_from=participant.time_from,
                time_to=participant.time_to,
                project_id=shift.project_id,
                shift_id=shift.oid,
                entity_id=participant.oid,
            )
        except Exception as exc:
            self._shift_participant_service.mark_reserve_failed(
                participant=participant,
                reason=str(exc),
                now=self._clock.now(),
            )
            message.status = OUTBOX_STATUS_COMPLETED
            message.attempts += 1
            message.last_error = str(exc)
            message.updated_at = self._clock.now()
            await self._shift_participants.update(participant)
            await self._reservation_outbox.update(message)
            await self._tx.commit()
            return ProcessReservationOutboxResult(status="failed", error=str(exc))

        self._shift_participant_service.mark_reserved(
            participant=participant,
            reservation_id=reservation_id,
            now=self._clock.now(),
        )
        participant.reserve_failure_reason = None
        message.status = OUTBOX_STATUS_COMPLETED
        message.attempts += 1
        message.last_error = None
        message.updated_at = self._clock.now()
        await self._shift_participants.update(participant)
        await self._reservation_outbox.update(message)
        await self._tx.commit()
        await publish_best_effort(
            publisher=self._publisher,
            topic="shift.participant_reserved",
            payload={
                "project_id": str(shift.project_id),
                "shift_id": str(shift.oid),
                "participant_id": str(participant.oid),
                "user_reservation_id": str(participant.user_reservation_id),
            },
        )
        return ProcessReservationOutboxResult(status="reserved")

    async def _process_resource_reserve(
        self,
        message: ReservationOutboxMessage,
    ) -> ProcessReservationOutboxResult:
        request = await self._resource_requests.get_by_id(message.aggregate_id)
        if request is None:
            return await self._complete_missing_message(message, "Resource request is not found.")
        if request.resource_reservation_id is not None:
            return await self._complete_message(message)
        if request.status.name != "RESERVING":
            return await self._complete_message(
                message,
                error=f"Resource request is in non-reserving status: {request.status.name}",
            )

        try:
            reservation_id = await self._user_service.reserve_resource_time(
                request_id=message.oid,
                owner_user_id=request.resource_owner_user_id,
                resource_id=request.resource_id,
                time_from=request.time_from,
                time_to=request.time_to,
                project_id=request.project_id,
                shift_id=request.shift_id,
                entity_id=request.oid,
            )
        except Exception as exc:
            self._resource_request_service.mark_reserve_failed(
                request=request,
                reason=str(exc),
                now=self._clock.now(),
            )
            message.status = OUTBOX_STATUS_COMPLETED
            message.attempts += 1
            message.last_error = str(exc)
            message.updated_at = self._clock.now()
            await self._resource_requests.update(request)
            await self._reservation_outbox.update(message)
            await self._tx.commit()
            return ProcessReservationOutboxResult(status="failed", error=str(exc))

        self._resource_request_service.mark_reserved(
            request=request,
            reservation_id=reservation_id,
            now=self._clock.now(),
        )
        request.reserve_failure_reason = None
        message.status = OUTBOX_STATUS_COMPLETED
        message.attempts += 1
        message.last_error = None
        message.updated_at = self._clock.now()
        await self._resource_requests.update(request)
        await self._reservation_outbox.update(message)
        await self._tx.commit()
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
        return ProcessReservationOutboxResult(status="reserved")

    async def _complete_message(
        self,
        message: ReservationOutboxMessage,
        *,
        error: str | None = None,
    ) -> ProcessReservationOutboxResult:
        message.status = OUTBOX_STATUS_COMPLETED
        message.last_error = error
        message.updated_at = self._clock.now()
        await self._reservation_outbox.update(message)
        await self._tx.commit()
        return ProcessReservationOutboxResult(status="completed", error=error)

    async def _complete_missing_message(
        self,
        message: ReservationOutboxMessage,
        error: str,
    ) -> ProcessReservationOutboxResult:
        message.status = OUTBOX_STATUS_COMPLETED
        message.attempts += 1
        message.last_error = error
        message.updated_at = self._clock.now()
        await self._reservation_outbox.update(message)
        await self._tx.commit()
        return ProcessReservationOutboxResult(status="failed", error=error)
