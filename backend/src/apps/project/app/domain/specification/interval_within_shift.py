from app.domain.entities import Shift
from app.domain.value_objects import TimeInterval


class IntervalWithinShiftSpecification:
    def is_satisfied(self, shift: Shift, interval: TimeInterval) -> bool:
        return shift.interval.contains(interval)
