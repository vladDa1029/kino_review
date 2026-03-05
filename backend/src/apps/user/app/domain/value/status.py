from dataclasses import dataclass

from app.domain.errors.value import AvailabilityStatusError
from app.domain.value.base import BaseValueObject


ALLOWED_STATUSES = {"free", "reserved", "blocked"}  # WARN:Может стоит ввести Еnum.


@dataclass(frozen=True, eq=False, unsafe_hash=True)
class AvailabilityStatus(BaseValueObject):
    value: str

    def _validate(self) -> None:
        if self.value not in ALLOWED_STATUSES:
            raise AvailabilityStatusError(f"Status not allowed: {self.value}")

    def __str__(self) -> str:
        return str(self.value)
