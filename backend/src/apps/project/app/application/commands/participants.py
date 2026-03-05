from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.application.ports.broker import EventPublisher
from app.application.ports.domain import (
    ClockPort,
    IdGeneratorPort,
    ProjectMemberRepository,
    ShiftParticipantRepository,
    ShiftRepository,
    UserServicePort,
)
from app.application.ports.transaction import TransactionManager
from app.application.support import (
    get_actor_member,
    publish_best_effort,
    require_participant,
    require_shift,
)
from app.domain.entities import ShiftParticipant
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
        self._shift_participant_service = shift_participant_service

    async def __call__(self, command: InviteShiftParticipantCommand) -> ShiftParticipant:
        now = self._clock.now()
        try:
            shift = await require_shift(shifts=self._shifts, shift_id=command.shift_id)
            await self._user_service.ensure_user_exists(command.participant_user_id)
            actor = await get_actor_member(
                project_members=self._project_members,
                project_id=shift.project_id,
                user_id=command.actor_user_id,
            )
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
        user_service: UserServicePort,
        shifts: ShiftRepository,
        shift_participants: ShiftParticipantRepository,
        shift_participant_service: ShiftParticipantService,
    ) -> None:
        self._tx = transaction_manager
        self._clock = clock
        self._publisher = publisher
        self._user_service = user_service
        self._shifts = shifts
        self._shift_participants = shift_participants
        self._shift_participant_service = shift_participant_service

    async def __call__(self, command: ConfirmShiftParticipantCommand) -> ShiftParticipant:
        now = self._clock.now()
        participant = await require_participant(
            shift_participants=self._shift_participants,
            participant_id=command.participant_id,
        )
        shift = await require_shift(shifts=self._shifts, shift_id=participant.shift_id)
        try:
            self._shift_participant_service.confirm(
                participant=participant,
                actor_user_id=command.actor_user_id,
                now=now,
            )
            self._shift_participant_service.mark_reserving(participant=participant, now=now)
            await self._shift_participants.update(participant)

            reservation_id = await self._user_service.reserve_user_time(
                user_id=participant.user_id,
                time_from=participant.time_from,
                time_to=participant.time_to,
                project_id=shift.project_id,
                shift_id=shift.oid,
                entity_id=participant.oid,
            )
            self._shift_participant_service.mark_reserved(
                participant=participant,
                reservation_id=reservation_id,
                now=self._clock.now(),
            )
            await self._shift_participants.update(participant)
            await self._tx.commit()
        except Exception as exc:
            failed_marked = await self._try_mark_reserve_failed(
                participant=participant,
                reason=str(exc),
            )
            if failed_marked:
                await self._tx.commit()
            else:
                await self._tx.rollback()
            raise

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
        return participant

    async def _try_mark_reserve_failed(self, *, participant: ShiftParticipant, reason: str) -> bool:
        try:
            self._shift_participant_service.mark_reserve_failed(
                participant=participant,
                reason=reason,
                now=self._clock.now(),
            )
            await self._shift_participants.update(participant)
            return True
        except Exception:
            return False


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
        shift_participant_service: ShiftParticipantService,
    ) -> None:
        self._tx = transaction_manager
        self._clock = clock
        self._publisher = publisher
        self._shift_participants = shift_participants
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
