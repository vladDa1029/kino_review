from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from app.domain.entities import ProjectMember, Shift, ShiftParticipant
from app.domain.enums import ProjectRole, ShiftParticipantStatus
from app.domain.errors.business import AccessDeniedError, StateTransitionError
from app.domain.policy.member_access import DirectorMemberPolicy
from app.domain.specification.interval_within_shift import IntervalWithinShiftSpecification
from app.domain.specification.shift_mutability import EditableShiftSpecification
from app.domain.value_objects import TimeInterval


@dataclass
class ShiftParticipantService:
    director_policy: DirectorMemberPolicy = field(default_factory=DirectorMemberPolicy)
    editable_shift_specification: EditableShiftSpecification = field(
        default_factory=EditableShiftSpecification
    )
    interval_within_shift_specification: IntervalWithinShiftSpecification = field(
        default_factory=IntervalWithinShiftSpecification
    )

    def invite(
        self,
        *,
        actor: ProjectMember,
        shift: Shift,
        participant_id: UUID,
        user_id: UUID,
        role: ProjectRole,
        time_from: datetime,
        time_to: datetime,
        now: datetime,
        existing: ShiftParticipant | None,
    ) -> ShiftParticipant:
        self.director_policy.check(actor, action="manage participants")
        if not self.editable_shift_specification.is_satisfied(shift):
            raise StateTransitionError("Participants can be changed only before shift approval.")

        participant_interval = TimeInterval(start=time_from, end=time_to)
        if not self.interval_within_shift_specification.is_satisfied(shift, participant_interval):
            raise StateTransitionError("Participant interval must be inside shift interval.")

        if existing and existing.status in {
            ShiftParticipantStatus.CONFIRMED,
            ShiftParticipantStatus.RESERVED,
            ShiftParticipantStatus.RESERVING,
        }:
            raise StateTransitionError("Participant already confirmed/reserved for this shift.")

        if existing:
            existing.time_from = time_from
            existing.time_to = time_to
            existing.status = ShiftParticipantStatus.INVITED
            existing.added_by = actor.user_id
            existing.role = role
            existing.user_reservation_id = None
            existing.reserve_failure_reason = None
            existing.updated_at = now
            return existing

        return ShiftParticipant(
            shift_id=shift.oid,
            user_id=user_id,
            role=role,
            time_from=time_from,
            time_to=time_to,
            status=ShiftParticipantStatus.INVITED,
            added_by=actor.user_id,
            oid=participant_id,
            created_at=now,
            updated_at=now,
        )

    def confirm(self, *, participant: ShiftParticipant, actor_user_id: UUID, now: datetime) -> None:
        if participant.user_id != actor_user_id:
            raise AccessDeniedError("Only participant user can confirm invitation.")
        if participant.status != ShiftParticipantStatus.INVITED:
            raise StateTransitionError("Only INVITED participant can be confirmed.")
        participant.status = ShiftParticipantStatus.CONFIRMED
        participant.updated_at = now

    def mark_reserving(self, *, participant: ShiftParticipant, now: datetime) -> None:
        if participant.status != ShiftParticipantStatus.CONFIRMED:
            raise StateTransitionError("Only CONFIRMED participant can move to RESERVING.")
        participant.status = ShiftParticipantStatus.RESERVING
        participant.updated_at = now

    def mark_reserved(
        self, *, participant: ShiftParticipant, reservation_id: UUID, now: datetime
    ) -> None:
        if participant.status != ShiftParticipantStatus.RESERVING:
            raise StateTransitionError("Only RESERVING participant can become RESERVED.")
        participant.status = ShiftParticipantStatus.RESERVED
        participant.user_reservation_id = reservation_id
        participant.reserve_failure_reason = None
        participant.updated_at = now

    def mark_reserve_failed(
        self, *, participant: ShiftParticipant, reason: str, now: datetime
    ) -> None:
        if participant.status != ShiftParticipantStatus.RESERVING:
            raise StateTransitionError("Only RESERVING participant can become RESERVE_FAILED.")
        participant.status = ShiftParticipantStatus.RESERVE_FAILED
        participant.reserve_failure_reason = reason
        participant.updated_at = now

    def decline(self, *, participant: ShiftParticipant, actor_user_id: UUID, now: datetime) -> None:
        if participant.user_id != actor_user_id:
            raise AccessDeniedError("Only participant user can decline invitation.")
        if participant.status != ShiftParticipantStatus.INVITED:
            raise StateTransitionError("Only INVITED participant can be declined.")
        participant.status = ShiftParticipantStatus.DECLINED
        participant.updated_at = now

    def cancel(self, *, actor: ProjectMember, participant: ShiftParticipant, now: datetime) -> None:
        self.director_policy.check(actor, action="manage participants")
        if participant.status in {
            ShiftParticipantStatus.CANCELLED,
            ShiftParticipantStatus.DECLINED,
        }:
            raise StateTransitionError("Participant invitation is already finalized.")
        participant.status = ShiftParticipantStatus.CANCELLED
        participant.updated_at = now
