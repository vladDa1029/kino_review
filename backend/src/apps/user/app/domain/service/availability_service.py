from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, List
from uuid import uuid4

from app.domain.entity.base import BaseId, Spare_time, User
from app.domain.errors.availability import (
    AvailabilityNotFoundError,
    ReservationOverlapError,
    WindowStatusError,
)
from app.domain.errors.value import TimeRangeError
from app.domain.policy.active_user import ActiveUserPolicy
from app.domain.policy.ownership import OwnershipPolicy
from app.domain.specification.time_overlap import NonOverlappingTimeSpec
from app.domain.specification.time_within import TimeWithinWindowSpec
from app.domain.value.status import AvailabilityStatus


def _default_id_factory() -> BaseId:
    return BaseId(uuid4())


@dataclass
class AvailabilityService:
    active_user_policy: ActiveUserPolicy = field(default_factory=ActiveUserPolicy)
    owner_policy: OwnershipPolicy = field(default_factory=OwnershipPolicy)
    overlap_spec: NonOverlappingTimeSpec = field(default_factory=NonOverlappingTimeSpec)
    within_spec: TimeWithinWindowSpec = field(default_factory=TimeWithinWindowSpec)
    id_factory: Callable[[], BaseId] = field(default_factory=lambda: _default_id_factory)

    def reserve(
        self,
        user: User,
        windows: List[Spare_time],
        owner_id: BaseId,
        obj_id: BaseId,
        start_time: datetime,
        end_time: datetime,
    ) -> List[Spare_time]:
        self.active_user_policy.check(user)
        self.owner_policy.check(user.oid, owner_id)
        if end_time <= start_time:
            raise TimeRangeError("End time must be after start time.")

        candidate = Spare_time(
            oid=self.id_factory(),
            obj=obj_id,
            start_time=start_time,
            end_time=end_time,
            status=AvailabilityStatus("reserved"),
        )

        free_windows = [
            window
            for window in windows
            if window.obj == obj_id
            and str(window.status) == "free"
            and self.within_spec.is_satisfied(window, candidate)
        ]
        if not free_windows:
            covered = [
                window
                for window in windows
                if window.obj == obj_id and self.within_spec.is_satisfied(window, candidate)
            ]
            if covered:
                raise WindowStatusError("Window status does not allow reservation.")
            raise AvailabilityNotFoundError("No free window for reservation.")

        reserved_windows = [
            window
            for window in windows
            if window.obj == obj_id and str(window.status) == "reserved"
        ]
        if not self.overlap_spec.is_satisfied(candidate, reserved_windows):
            raise ReservationOverlapError("Reservation overlaps existing segment.")

        free_window = free_windows[0]
        windows.remove(free_window)

        if free_window.start_time < candidate.start_time:
            windows.append(
                Spare_time(
                    oid=self.id_factory(),
                    obj=obj_id,
                    start_time=free_window.start_time,
                    end_time=candidate.start_time,
                    status=AvailabilityStatus("free"),
                )
            )

        windows.append(candidate)

        if candidate.end_time < free_window.end_time:
            windows.append(
                Spare_time(
                    oid=self.id_factory(),
                    obj=obj_id,
                    start_time=candidate.end_time,
                    end_time=free_window.end_time,
                    status=AvailabilityStatus("free"),
                )
            )

        return windows
