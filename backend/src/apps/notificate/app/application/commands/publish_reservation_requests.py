from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.application.ports.broker import EventPublisher

PARTICIPANT_RESERVATION_REQUESTED_TOPIC = "shift.participant_reservation_requested"
RESOURCE_RESERVATION_REQUESTED_TOPIC = "shift.resource_request_reservation_requested"


@dataclass(frozen=True, slots=True, kw_only=True)
class PublishParticipantReservationRequestedCommand:
    request_id: UUID
    project_id: UUID
    shift_id: UUID
    participant_id: UUID
    user_id: UUID
    time_from: datetime
    time_to: datetime


class PublishParticipantReservationRequestedHandler:
    def __init__(self, *, publisher: EventPublisher) -> None:
        self._publisher = publisher

    async def __call__(self, command: PublishParticipantReservationRequestedCommand) -> None:
        await self._publisher.publish(
            PARTICIPANT_RESERVATION_REQUESTED_TOPIC,
            {
                "request_id": str(command.request_id),
                "project_id": str(command.project_id),
                "shift_id": str(command.shift_id),
                "participant_id": str(command.participant_id),
                "user_id": str(command.user_id),
                "start_time": command.time_from.isoformat(),
                "end_time": command.time_to.isoformat(),
            },
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class PublishResourceReservationRequestedCommand:
    request_id: UUID
    project_id: UUID
    shift_id: UUID
    resource_request_id: UUID
    owner_user_id: UUID
    resource_id: UUID
    resource_type: str
    time_from: datetime
    time_to: datetime


class PublishResourceReservationRequestedHandler:
    def __init__(self, *, publisher: EventPublisher) -> None:
        self._publisher = publisher

    async def __call__(self, command: PublishResourceReservationRequestedCommand) -> None:
        await self._publisher.publish(
            RESOURCE_RESERVATION_REQUESTED_TOPIC,
            {
                "request_id": str(command.request_id),
                "project_id": str(command.project_id),
                "shift_id": str(command.shift_id),
                "resource_request_id": str(command.resource_request_id),
                "owner_user_id": str(command.owner_user_id),
                "resource_id": str(command.resource_id),
                "resource_type": command.resource_type,
                "start_time": command.time_from.isoformat(),
                "end_time": command.time_to.isoformat(),
            },
        )
