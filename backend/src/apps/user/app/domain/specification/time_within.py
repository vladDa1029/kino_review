from app.domain.entity.base import Spare_time


class TimeWithinWindowSpec:
    def is_satisfied(self, outer: Spare_time, inner: Spare_time) -> bool:
        return (
            inner.start_time >= outer.start_time
            and inner.end_time <= outer.end_time
        )
