from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from app.domain.entities import ProjectMember, Shift
from app.domain.enums import ShiftStatus
from app.domain.errors.business import StateTransitionError
from app.domain.policy.member_access import DirectorMemberPolicy
from app.domain.value_objects import TimeInterval


@dataclass
class ShiftService:
    director_policy: DirectorMemberPolicy = field(default_factory=DirectorMemberPolicy)

    def create_shift(
        self,
        *,
        actor: ProjectMember,
        shift_id: UUID,
        project_id: UUID,
        title: str,
        description: str,
        start_time: datetime,
        end_time: datetime,
        now: datetime,
    ) -> Shift:
        self.director_policy.check(actor, action="manage shifts")
        TimeInterval(start=start_time, end=end_time)
        return Shift(
            project_id=project_id,
            title=title.strip(),
            description=description.strip(),
            start_time=start_time,
            end_time=end_time,
            created_by=actor.user_id,
            status=ShiftStatus.DRAFT,
            oid=shift_id,
            created_at=now,
            updated_at=now,
        )

    def update_shift(
        self,
        *,
        actor: ProjectMember,
        shift: Shift,
        title: str,
        description: str,
        start_time: datetime,
        end_time: datetime,
        now: datetime,
    ) -> None:
        self.director_policy.check(actor, action="manage shifts")
        if shift.status != ShiftStatus.DRAFT:
            raise StateTransitionError("Only DRAFT shift can be edited.")
        TimeInterval(start=start_time, end=end_time)
        shift.title = title.strip()
        shift.description = description.strip()
        shift.start_time = start_time
        shift.end_time = end_time
        shift.updated_at = now

    def request_approval(self, *, actor: ProjectMember, shift: Shift, now: datetime) -> None:
        self.director_policy.check(actor, action="manage shifts")
        if shift.status != ShiftStatus.DRAFT:
            raise StateTransitionError("Only DRAFT shift can be moved to PENDING_APPROVAL.")
        shift.status = ShiftStatus.PENDING_APPROVAL
        shift.updated_at = now

    def approve_shift(self, *, actor: ProjectMember, shift: Shift, now: datetime) -> None:
        self.director_policy.check(actor, action="manage shifts")
        if shift.status not in {ShiftStatus.DRAFT, ShiftStatus.PENDING_APPROVAL}:
            raise StateTransitionError("Only DRAFT/PENDING_APPROVAL shift can be approved.")
        shift.status = ShiftStatus.APPROVED
        shift.approved_by = actor.user_id
        shift.approved_at = now
        shift.updated_at = now

    def cancel_shift(self, *, actor: ProjectMember, shift: Shift, now: datetime) -> None:
        self.director_policy.check(actor, action="manage shifts")
        if shift.status in {ShiftStatus.CANCELLED, ShiftStatus.COMPLETED}:
            raise StateTransitionError("Shift is already finalized.")
        shift.status = ShiftStatus.CANCELLED
        shift.updated_at = now

    def complete_shift(self, *, actor: ProjectMember, shift: Shift, now: datetime) -> None:
        self.director_policy.check(actor, action="manage shifts")
        if shift.status != ShiftStatus.APPROVED:
            raise StateTransitionError("Only APPROVED shift can be completed.")
        shift.status = ShiftStatus.COMPLETED
        shift.updated_at = now
