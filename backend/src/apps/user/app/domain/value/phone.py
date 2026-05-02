import re
from dataclasses import dataclass

from app.domain.errors.value import PhoneError
from app.domain.value.base import BaseValueObject


@dataclass(frozen=True, eq=False, unsafe_hash=True)
class Phone(BaseValueObject):
    value: str

    def _validate(self):
        phone_validate_pattern = (
            r"^(8|\+7)(\s|\(|-)?(\d{3})(\s|\)|-)?(\d{3})(\s|-)?(\d{2})(\s|-)?(\d{2})$"
        )

        if not re.match(phone_validate_pattern, self.value):
            raise PhoneError(f"Phonr not valid {self.value}")

    def __str__(self) -> str:
        return str(self.value)
