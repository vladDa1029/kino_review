from abc import ABC
from dataclasses import dataclass, field
from datetime import UTC, datetime
import re
from typing import NewType
from uuid import UUID

from app.domain.values import Email


BaseUserId = NewType("BaseUserId", UUID)


@dataclass
class Base(ABC):
    oid: BaseUserId

    def __eq__(self, other) -> bool:
        if isinstance(other, Base):
            return other.oid == self.oid
        return False

    def __hash__(self):
        return hash(self.oid)


@dataclass
class User(Base):
    email: Email
    password: str  # не могу про валидировать здесь уже хеш пароля возможно стот в начале передавать пароль а потом хешировать
    is_active: bool = True
    is_superuser: bool = False
    is_verified: bool = False
    create_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __str__(self):
        return (
            f"User is : oid {self.oid}, username {self.username}, email : {self.email}."
        )
