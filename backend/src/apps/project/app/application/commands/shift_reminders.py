from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID, uuid5

import structlog

from app.application.ports.broker import EventPublisher
from app.application.ports.domain import (
    ClockPort,
    IdGeneratorPort,
    ProjectRepository,
    ResourceRequestRepository,
    ShiftParticipantRepository,
    ShiftReminderRepository,
    ShiftRepository,
)
from app.application.ports.transaction import TransactionManager
from app.config import ShiftReminder as ShiftReminderSettings
from app.domain.entities import Shift, ShiftParticipant, ShiftReminder, ShiftResourceRequest
from app.domain.enums import (
    ProjectRole,
    ResourceRequestStatus,
    ShiftParticipantStatus,
    ShiftReminderStatus,
    ShiftStatus,
)

log = structlog.get_logger(__name__)

SHIFT_REMINDER_REQUESTED_TOPIC = "shift.reminder_requested"

# Deterministic namespace so a re-published reminder reuses the same notification id.
SHIFT_REMINDER_NAMESPACE = UUID("b6c0d2f4-1e3a-4c5b-9d8e-7f0a1b2c3d4e")

# Participants that are expected to attend the shift.
_NOTIFIABLE_PARTICIPANT_STATUSES = {
    ShiftParticipantStatus.CONFIRMED,
    ShiftParticipantStatus.RESERVING,
    ShiftParticipantStatus.RESERVED,
}

# Resource requests the owner is expected to bring to the shift.
_NOTIFIABLE_RESOURCE_STATUSES = {
    ResourceRequestStatus.APPROVED_OWNER,
    ResourceRequestStatus.RESERVING,
    ResourceRequestStatus.RESERVED,
}


def build_reminder_notification_id(*, reminder_id: UUID, participant_id: UUID) -> UUID:
    return uuid5(SHIFT_REMINDER_NAMESPACE, f"{reminder_id}:{participant_id}")


async def upsert_shift_reminder(
    *,
    shift_reminders: ShiftReminderRepository,
    clock: ClockPort,
    id_generator: IdGeneratorPort,
    settings: ShiftReminderSettings,
    shift: Shift,
) -> None:
    """Create or refresh the pending reminder for an approved shift.

    ``fire_at`` is ``start_time - offset`` so the worker can pick it up once the
    send time is reached. A repeated approval reuses the existing row (unique on
    ``shift_id``) and resets it back to ``PENDING``.
    """
    now = clock.now()
    fire_at = shift.start_time - timedelta(seconds=settings.offset_seconds)
    existing = await shift_reminders.get_by_shift(shift.oid)
    if existing is not None:
        existing.fire_at = fire_at
        existing.status = ShiftReminderStatus.PENDING
        existing.updated_at = now
        await shift_reminders.update(existing)
        return
    await shift_reminders.add(
        ShiftReminder(
            oid=id_generator(),
            shift_id=shift.oid,
            fire_at=fire_at,
            status=ShiftReminderStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
    )


async def cancel_shift_reminder(
    *,
    shift_reminders: ShiftReminderRepository,
    clock: ClockPort,
    shift_id: UUID,
) -> None:
    """Cancel a still-pending reminder (e.g. when its shift gets cancelled)."""
    reminder = await shift_reminders.get_by_shift(shift_id)
    if reminder is None or reminder.status != ShiftReminderStatus.PENDING:
        return
    reminder.status = ShiftReminderStatus.CANCELLED
    reminder.updated_at = clock.now()
    await shift_reminders.update(reminder)


class ProcessShiftRemindersHandler:
    """Worker entry point: dispatch reminders whose send time has arrived."""

    def __init__(
        self,
        *,
        transaction_manager: TransactionManager,
        clock: ClockPort,
        publisher: EventPublisher,
        projects: ProjectRepository,
        shifts: ShiftRepository,
        shift_participants: ShiftParticipantRepository,
        resource_requests: ResourceRequestRepository,
        shift_reminders: ShiftReminderRepository,
    ) -> None:
        self._tx = transaction_manager
        self._clock = clock
        self._publisher = publisher
        self._projects = projects
        self._shifts = shifts
        self._shift_participants = shift_participants
        self._resource_requests = resource_requests
        self._shift_reminders = shift_reminders

    async def __call__(self, *, limit: int = 20) -> int:
        now = self._clock.now()
        reminders = await self._shift_reminders.list_due(now=now, limit=limit)
        processed = 0
        for reminder in reminders:
            await self._process_reminder(reminder.oid)
            processed += 1
        return processed

    async def _process_reminder(self, reminder_id: UUID) -> None:
        reminder = await self._shift_reminders.get_by_id(reminder_id)
        if reminder is None or reminder.status != ShiftReminderStatus.PENDING:
            return

        shift = await self._shifts.get_by_id(reminder.shift_id)
        if shift is None or shift.status != ShiftStatus.APPROVED:
            # The shift was cancelled/never confirmed; drop the reminder.
            await self._finalize(reminder, ShiftReminderStatus.CANCELLED)
            return

        project = await self._projects.get_by_id(shift.project_id)
        participants = await self._shift_participants.list_by_shift(shift.oid)
        resource_requests = await self._resource_requests.list_by_shift(shift.oid)

        events = self._build_events(
            reminder_id=reminder.oid,
            shift=shift,
            project_title=project.title if project is not None else "",
            participants=participants,
            resource_requests=resource_requests,
        )
        for payload in events:
            await self._publisher.publish(SHIFT_REMINDER_REQUESTED_TOPIC, payload)

        await self._finalize(reminder, ShiftReminderStatus.SENT)
        log.info(
            "shift.reminder.dispatched",
            shift_id=str(shift.oid),
            reminder_id=str(reminder.oid),
            recipients=len(events),
        )

    def _build_events(
        self,
        *,
        reminder_id: UUID,
        shift: Shift,
        project_title: str,
        participants: list[ShiftParticipant],
        resource_requests: list[ShiftResourceRequest],
    ) -> list[dict]:
        resources_by_owner: dict[UUID, list[ShiftResourceRequest]] = {}
        for request in resource_requests:
            if request.status not in _NOTIFIABLE_RESOURCE_STATUSES:
                continue
            resources_by_owner.setdefault(request.resource_owner_user_id, []).append(request)

        events: list[dict] = []
        for participant in participants:
            if participant.status not in _NOTIFIABLE_PARTICIPANT_STATUSES:
                continue
            owned = resources_by_owner.get(participant.user_id, [])
            events.append(
                {
                    "notification_id": str(
                        build_reminder_notification_id(
                            reminder_id=reminder_id,
                            participant_id=participant.oid,
                        )
                    ),
                    "project_id": str(shift.project_id),
                    "project_title": project_title,
                    "shift_id": str(shift.oid),
                    "shift_title": shift.title,
                    "shift_description": shift.description,
                    "start_time": shift.start_time.isoformat(),
                    "end_time": shift.end_time.isoformat(),
                    "user_id": str(participant.user_id),
                    "role": _role_name(participant.role),
                    "resources": [
                        {
                            "resource_type": request.resource_type,
                            "time_from": request.time_from.isoformat(),
                            "time_to": request.time_to.isoformat(),
                        }
                        for request in owned
                    ],
                }
            )
        return events

    async def _finalize(self, reminder: ShiftReminder, status: ShiftReminderStatus) -> None:
        reminder.status = status
        reminder.updated_at = self._clock.now()
        await self._shift_reminders.update(reminder)
        await self._tx.commit()


def _role_name(role: object) -> str:
    if hasattr(role, "name"):
        return str(getattr(role, "name"))
    return ProjectRole(int(role)).name
