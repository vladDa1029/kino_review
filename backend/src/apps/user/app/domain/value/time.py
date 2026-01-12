from dataclasses import dataclass
from datetime import datetime

from app.domain.constant import MIN_SPARE_TIME
from app.domain.value.base import BaseValueObject


@dataclass(frozen=True, eq=False, unsafe_hash=True)
class Time(BaseValueObject):
    start_time: datetime
    end_time: datetime

    def _validate(self):
        if not self.end_time > self.start_time:
            raise ...
        elif not (self.end_time - self.start_time) >= MIN_SPARE_TIME:
            raise ...
