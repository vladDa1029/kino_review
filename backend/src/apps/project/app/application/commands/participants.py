from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.application.commands.reservation_outbox import (
    OUTBOX_STATUS_PENDING,
    PARTICIPANT_RESERVE_OPERATION,
    build_participant_reservation_request_id,
)
from app.application.ports.broker import EventPublisher
from app.application.ports.domain import (
    ClockPort,
    IdGeneratorPort,
    ProjectMemberRepository,
    ReservationOutboxRepository,
    ShiftParticipantRepository,
    ShiftReportRepository,
    ShiftRepository,
    UserServicePort,
)
from app.application.ports.transaction import TransactionManager
from app.application.reports_support import mark_shift_reports_stale
from app.application.support import (
    get_actor_member,
    publish_best_effort,
    require_active_project_member,
    require_participant,
    require_shift,
)
from app.domain.entities import ReservationOutboxMessage, ShiftParticipant
from app.domain.enums import ProjectRole
from app.domain.services import ShiftParticipantService


@dataclass(frozen=True, slots=True, kw_only=True)
class InviteShiftParticipantCommand:
    shift_id: UUID
    actor_user_id: UUID
    participant_user_id: UUID
    role: ProjectRole
    time_from: datetime
    time_to: datetime


class InviteShiftParticipantHandler:
    def __init__(
        self,
        *,
        transaction_manager: TransactionManager,
        clock: ClockPort,
        id_generator: IdGeneratorPort,
        publisher: EventPublisher,
        user_service: UserServicePort,
        project_members: ProjectMemberRepository,
        shifts: ShiftRepository,
        shift_participants: ShiftParticipantRepository,
        shift_reports: ShiftReportRepository,
        shift_participant_service: ShiftParticipantService,
    ) -> None:
        self._tx = transaction_manager
        self._clock = clock
        self._id_generator = id_generator
        self._publisher = publisher
        self._user_service = user_service
        self._project_members = project_members
        self._shifts = shifts
        self._shift_participants = shift_participants
        self._shift_reports = shift_reports
        self._shift_participant_service = shift_participant_service

    async def __call__(self, command: InviteShiftParticipantCommand) -> ShiftParticipant:
        now = self._clock.now()
        try:
            shift = await require_shift(shifts=self._shifts, shift_id=command.shift_id)
            actor = await get_actor_member(
                project_members=self._project_members,
                project_id=shift.project_id,
                user_id=command.actor_user_id,
            )
            target = await require_active_project_member(
                project_members=self._project_members,
                project_id=shift.project_id,
                user_id=command.participant_user_id,
                message="Participant user is not an active project member.",
            )
            await self._user_service.ensure_user_exists(target.user_id)
            existing = await self._shift_participants.get_by_shift_and_user(
                shift_id=command.shift_id,
                user_id=command.participant_user_id,
            )
            participant = self._shift_participant_service.invite(
                actor=actor,
                shift=shift,
                participant_id=self._id_generator(),
                user_id=command.participant_user_id,
                role=command.role,
                time_from=command.time_from,
                time_to=command.time_to,
                now=now,
                existing=existing,
            )
            if existing is None:
                await self._shift_participants.add(participant)
            else:
                await self._shift_participants.update(participant)
            await mark_shift_reports_stale(
                shift_reports=self._shift_reports,
                clock=self._clock,
                shift_id=shift.oid,
                reason="Participant composition changed.",
            )
            await self._tx.commit()
        except Exception:
            await self._tx.rollback()
            raise

        await publish_best_effort(
            publisher=self._publisher,
            topic="shift.participant_invited",
            payload={
                "project_id": str(shift.project_id),
                "shift_id": str(shift.oid),
                "participant_user_id": str(command.participant_user_id),
                "participant_id": str(participant.oid),
            },
        )
        return participant


@dataclass(frozen=True, slots=True, kw_only=True)
class ConfirmShiftParticipantCommand:
    participant_id: UUID
    actor_user_id: UUID


class ConfirmShiftParticipantHandler:
    def __init__(
        self,
        *,
        transaction_manager: TransactionManager,
        clock: ClockPort,
        publisher: EventPublisher,
        reservation_outbox: ReservationOutboxRepository,
        project_members: ProjectMemberRepository,
        shifts: ShiftRepository,
        shift_participants: ShiftParticipantRepository,
        shift_reports: ShiftReportRepository,
        shift_participant_service: ShiftParticipantService,
    ) -> None:
        self._tx = transaction_manager
        self._clock = clock
        self._publisher = publisher
        self._reservation_outbox = reservation_outbox
        self._project_members = project_members
        self._shifts = shifts
        self._shift_participants = shift_participants
        self._shift_reports = shift_reports
        self._shift_participant_service = shift_participant_service

    async def __call__(self, command: ConfirmShiftParticipantCommand) -> ShiftParticipant:
        now = self._clock.now()
        participant = await require_participant(
            shift_participants=self._shift_participants,
            participant_id=command.participant_id,
        )
        shift = await require_shift(shifts=self._shifts, shift_id=participant.shift_id)
        await require_active_project_member(
            project_members=self._project_members,
            project_id=shift.project_id,
            user_id=participant.user_id,
            message="Participant user is not an active project member.",
        )
        request_id = build_participant_reservation_request_id(participant.oid)
        try:
            self._shift_participant_service.confirm(
                participant=participant,
                actor_user_id=command.actor_user_id,
                now=now,
            )
            self._shift_participant_service.mark_reserving(participant=participant, now=now)
            await self._shift_participants.update(participant)
            existing_outbox = await self._reservation_outbox.get_by_id(request_id)
            if existing_outbox is not None:
                # Re-invite + re-confirm cycle: reset the completed entry back to
                # pending so the outbox poller will pick it up again.
                existing_outbox.status = OUTBOX_STATUS_PENDING
                existing_outbox.attempts = 0
                existing_outbox.last_error = None
                existing_outbox.updated_at = now
                await self._reservation_outbox.update(existing_outbox)
            else:
                await self._reservation_outbox.add(
                    ReservationOutboxMessage(
                        oid=request_id,
                        operation=PARTICIPANT_RESERVE_OPERATION,
                        aggregate_id=participant.oid,
                        status=OUTBOX_STATUS_PENDING,
                        attempts=0,
                        created_at=now,
                        updated_at=now,
                    )
                )
            await mark_shift_reports_stale(
                shift_reports=self._shift_reports,
                clock=self._clock,
                shift_id=shift.oid,
                reason="Participant status changed.",
            )
            await self._tx.commit()
        except Exception:
            await self._tx.rollback()
            raise

        return participant


@dataclass(frozen=True, slots=True, kw_only=True)
class DeclineShiftParticipantCommand:
    participant_id: UUID
    actor_user_id: UUID


class DeclineShiftParticipantHandler:
    def __init__(
        self,
        *,
        transaction_manager: TransactionManager,
        clock: ClockPort,
        publisher: EventPublisher,
        shift_participants: ShiftParticipantRepository,
        shift_reports: ShiftReportRepository,
        shifts: ShiftRepository,
        shift_participant_service: ShiftParticipantService,
    ) -> None:
        self._tx = transaction_manager
        self._clock = clock
        self._publisher = publisher
        self._shift_participants = shift_participants
        self._shift_reports = shift_reports
        self._shifts = shifts
        self._shift_participant_service = shift_participant_service

    async def __call__(self, command: DeclineShiftParticipantCommand) -> ShiftParticipant:
        now = self._clock.now()
        try:
            participant = await require_participant(
                shift_participants=self._shift_participants,
                participant_id=command.participant_id,
            )
            self._shift_participant_service.decline(
                participant=participant,
                actor_user_id=command.actor_user_id,
                now=now,
            )
            await self._shift_participants.update(participant)
            shift = await require_shift(shifts=self._shifts, shift_id=participant.shift_id)
            await mark_shift_reports_stale(
                shift_reports=self._shift_reports,
                clock=self._clock,
                shift_id=shift.oid,
                reason="Participant status changed.",
            )
            await self._tx.commit()
        except Exception:
            await self._tx.rollback()
            raise

        await publish_best_effort(
            publisher=self._publisher,
            topic="shift.participant_declined",
            payload={
                "shift_id": str(participant.shift_id),
                "participant_id": str(participant.oid),
                "user_id": str(participant.user_id),
            },
        )
        return participant
