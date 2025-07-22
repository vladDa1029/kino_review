from abc import ABC
from dataclasses import dataclass
import re
from uuid import UUID


@dataclass
class Base(ABC):
    oid: UUID

    def __eq__(self, other) -> bool:
        if isinstance(other, Base):
            return other.oid == self.oid
        return False

    def __hash__(self):
        return hash(self.oid)


@dataclass
class User(Base):
    email: str
    password: str
    is_active: bool = False
    is_superuser: bool = False
    is_verified: bool = False

    def __post_init__(self):
        self.validate_email()

    def validate_email(self) -> None:
        if not self.email:
            raise ValueError("Почта не должна быть пустой")

        email_validate_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

        if not re.match(email_validate_pattern, self.email):
            raise ValueError(f"Почта не валидна {self.email}")

    def validate_password(self) -> None:
        if not self.password:
            raise ValueError("Пароль должен быть введён")

        value_length = len(self.password)

        if value_length not in range(3, 100):
            raise ValueError(
                f"Длина пароля от 3 до 100 символов а у вас {str(value_length)}"
            )
