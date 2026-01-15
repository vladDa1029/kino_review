from dataclasses import dataclass
from datetime import datetime

from app.domain.constant import MIN_SPARE_TIME
from app.domain.errors.value import MinSpareTimeError, TimeRangeError
from app.domain.value.base import BaseValueObject


@dataclass(frozen=True, eq=False, unsafe_hash=True)
class Time(BaseValueObject):
    start_time: datetime
    end_time: datetime

    def _validate(self):
        if self.end_time <= self.start_time:
            raise TimeRangeError("End time must be after start time.")
        if (self.end_time - self.start_time) < MIN_SPARE_TIME:
            raise MinSpareTimeError("Time range is shorter than minimal duration.")

    def __str__(self) -> str:
        return f"{self.start_time.isoformat()}-{self.end_time.isoformat()}"
