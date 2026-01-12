from dataclasses import dataclass
import re

from app.domain.errors.value import EmailError
from app.domain.value.base import BaseValueObject


@dataclass(frozen=True, eq=False, unsafe_hash=True)
class Email(BaseValueObject):
    value: str

    def _validate(self):
        email_validate_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

        if not re.match(email_validate_pattern, self.value):
            raise EmailError(f"Email not valid {self.value}")

    def __str__(self) -> str:
        return str(self.value)
