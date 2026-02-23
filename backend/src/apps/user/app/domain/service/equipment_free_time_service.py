from dataclasses import dataclass, field
from typing import List, Protocol

from app.domain.entity.base import BaseId, Spare_time, User
from app.domain.errors.aggregate import CrossingTimingError
from app.domain.policy.active_user import ActiveUserPolicy
from app.domain.policy.ownership import OwnershipPolicy
from app.domain.specification.time_overlap import NonOverlappingTimeSpec


class OwnedEquipment(Protocol):
    oid: BaseId
    users_id: BaseId


@dataclass
class EquipmentFreeTimeService:
    active_user_policy: ActiveUserPolicy = field(default_factory=ActiveUserPolicy)
    owner_policy: OwnershipPolicy = field(default_factory=OwnershipPolicy)
    overlap_spec: NonOverlappingTimeSpec = field(default_factory=NonOverlappingTimeSpec)

    def add_timing(
        self,
        user: User,
        equipment: OwnedEquipment,
        timings: List[Spare_time],
        new_timing: Spare_time,
    ) -> List[Spare_time]:
        self.active_user_policy.check(user)
        self.owner_policy.check(user.oid, equipment.users_id)
        self.owner_policy.check(equipment.oid, new_timing.obj)

        equipment_timings = [
            timing for timing in timings if timing.obj == equipment.oid
        ]
        if not self.overlap_spec.is_satisfied(new_timing, equipment_timings):
            raise CrossingTimingError("New timing overlaps existing timing.")

        timings.append(new_timing)
        return timings
