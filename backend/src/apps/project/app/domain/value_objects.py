from dataclasses import dataclass
from datetime import datetime

from app.domain.errors.business import DomainInvariantError


@dataclass(frozen=True, slots=True)
class TimeInterval:
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.end <= self.start:
            raise DomainInvariantError("Invalid interval: end must be greater than start.")

    def overlaps(self, other: "TimeInterval") -> bool:
        # [start, end) semantics.
        return self.start < other.end and other.start < self.end

    def contains(self, other: "TimeInterval") -> bool:
        return self.start <= other.start and other.end <= self.end
