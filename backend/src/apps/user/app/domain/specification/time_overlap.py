from typing import Iterable

from app.domain.entity.base import Spare_time


class NonOverlappingTimeSpec:
    def is_satisfied(
        self, new_timing: Spare_time, existing: Iterable[Spare_time]
    ) -> bool:
        for time in existing:
            if not (
                new_timing.end_time < time.start_time
                or new_timing.start_time > time.end_time
            ):
                return False
        return True
