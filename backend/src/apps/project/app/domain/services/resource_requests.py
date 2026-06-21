from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from app.domain.entities import ProjectMember, Shift, ShiftResourceRequest
from app.domain.enums import ProjectRole, ResourceRequestStatus, ShiftStatus
from app.domain.errors.business import AccessDeniedError, StateTransitionError
from app.domain.policy.member_access import ActiveMemberPolicy
from app.domain.specification.interval_within_shift import IntervalWithinShiftSpecification
from app.domain.value_objects import TimeInterval


@dataclass
class ResourceRequestService:
    active_member_policy: ActiveMemberPolicy = field(default_factory=ActiveMemberPolicy)
    interval_within_shift_specification: IntervalWithinShiftSpecification = field(
        default_factory=IntervalWithinShiftSpecification
    )

    REQUEST_ALLOWED_ROLES = {
        ProjectRole.DIRECTOR,
        ProjectRole.PROP_MASTER,
        ProjectRole.CAMERA,
        ProjectRole.SOUND,
        ProjectRole.LIGHT,
    }

    def create(
        self,
        *,
        actor: ProjectMember,
        request_id: UUID,
        shift: Shift,
        resource_type: str,
        resource_id: UUID,
        resource_owner_user_id: UUID,
        time_from: datetime,
        time_to: datetime,
        now: datetime,
    ) -> ShiftResourceRequest:
        self.active_member_policy.check(actor, action="create resource requests")
        if actor.role not in self.REQUEST_ALLOWED_ROLES:
            raise AccessDeniedError("Actor role cannot request resources.")
        if shift.status not in {
            ShiftStatus.DRAFT,
            ShiftStatus.PENDING_APPROVAL,
            ShiftStatus.APPROVED,
        }:
            raise StateTransitionError("Resource request is not allowed for shift current status.")

        requested_interval = TimeInterval(start=time_from, end=time_to)
        if not self.interval_within_shift_specification.is_satisfied(shift, requested_interval):
            raise StateTransitionError("Requested resource interval must be inside shift interval.")

        return ShiftResourceRequest(
            project_id=shift.project_id,
            shift_id=shift.oid,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_owner_user_id=resource_owner_user_id,
            requested_by_user_id=actor.user_id,
            time_from=time_from,
            time_to=time_to,
            status=ResourceRequestStatus.PENDING_OWNER,
            oid=request_id,
            created_at=now,
            updated_at=now,
        )

    def approve(self, *, request: ShiftResourceRequest, actor_user_id: UUID, now: datetime) -> None:
        if request.resource_owner_user_id != actor_user_id:
            raise AccessDeniedError("Only resource owner can approve request.")
        if request.status != ResourceRequestStatus.PENDING_OWNER:
            raise StateTransitionError("Only PENDING_OWNER request can be approved.")
        request.status = ResourceRequestStatus.APPROVED_OWNER
        request.rejection_reason = None
        request.updated_at = now

    def reject(
        self,
        *,
        request: ShiftResourceRequest,
        actor_user_id: UUID,
        reason: str,
        now: datetime,
    ) -> None:
        if request.resource_owner_user_id != actor_user_id:
            raise AccessDeniedError("Only resource owner can reject request.")
        if request.status != ResourceRequestStatus.PENDING_OWNER:
            raise StateTransitionError("Only PENDING_OWNER request can be rejected.")
        request.status = ResourceRequestStatus.REJECTED_OWNER
        request.rejection_reason = reason.strip() or "Rejected by owner."
        request.updated_at = now

    def cancel(
        self,
        *,
        request: ShiftResourceRequest,
        actor: ProjectMember,
        now: datetime,
    ) -> None:
        self.active_member_policy.check(actor, action="cancel resource requests")
        is_requester = request.requested_by_user_id == actor.user_id
        is_director = actor.role == ProjectRole.DIRECTOR
        if not (is_requester or is_director):
            raise AccessDeniedError("Only the request author or a director can cancel the request.")
        if request.status == ResourceRequestStatus.RESERVED:
            raise StateTransitionError(
                "Reserved resource request cannot be cancelled without explicit confirmation."
            )
        if request.status not in {
            ResourceRequestStatus.PENDING_OWNER,
            ResourceRequestStatus.APPROVED_OWNER,
        }:
            raise StateTransitionError("Resource request cannot be cancelled in its current status.")
        request.status = ResourceRequestStatus.CANCELLED
        request.updated_at = now

    def cancel_due_to_shift(self, *, request: ShiftResourceRequest, now: datetime) -> bool:
        """Cancel a request because its shift is being cancelled.

        Returns ``True`` when a reservation cancellation must be dispatched
        (the request had already been reserved on the user side).
        """
        if request.status in {
            ResourceRequestStatus.CANCELLED,
            ResourceRequestStatus.REJECTED_OWNER,
        }:
            return False
        needs_reservation_cancel = request.resource_reservation_id is not None
        request.status = ResourceRequestStatus.CANCELLED
        request.updated_at = now
        return needs_reservation_cancel

    def cancel_unsettled_on_approval(
        self, *, request: ShiftResourceRequest, now: datetime
    ) -> bool:
        """Cancel a resource request that is not reserved when its shift is approved.

        Only RESERVED requests are kept on an approved shift; anything still awaiting
        the owner or its reservation (PENDING_OWNER, APPROVED_OWNER, RESERVING) or
        whose reservation failed (RESERVE_FAILED) is moved to CANCELLED. Returns
        ``True`` when a reservation cancellation must be dispatched.
        """
        if request.status in {
            ResourceRequestStatus.RESERVED,
            ResourceRequestStatus.CANCELLED,
            ResourceRequestStatus.REJECTED_OWNER,
        }:
            return False
        needs_reservation_cancel = request.resource_reservation_id is not None
        request.status = ResourceRequestStatus.CANCELLED
        request.updated_at = now
        return needs_reservation_cancel

    def mark_reserving(self, *, request: ShiftResourceRequest, now: datetime) -> None:
        if request.status != ResourceRequestStatus.APPROVED_OWNER:
            raise StateTransitionError("Only APPROVED_OWNER request can move to RESERVING.")
        request.status = ResourceRequestStatus.RESERVING
        request.updated_at = now

    def mark_reserved(
        self, *, request: ShiftResourceRequest, reservation_id: UUID, now: datetime
    ) -> None:
        if request.status != ResourceRequestStatus.RESERVING:
            raise StateTransitionError("Only RESERVING request can become RESERVED.")
        request.status = ResourceRequestStatus.RESERVED
        request.resource_reservation_id = reservation_id
        request.reserve_failure_reason = None
        request.updated_at = now

    def mark_reserve_failed(
        self, *, request: ShiftResourceRequest, reason: str, now: datetime
    ) -> None:
        if request.status != ResourceRequestStatus.RESERVING:
            raise StateTransitionError("Only RESERVING request can become RESERVE_FAILED.")
        request.status = ResourceRequestStatus.RESERVE_FAILED
        request.reserve_failure_reason = reason
        request.updated_at = now
