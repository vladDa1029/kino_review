from abc import ABC
from dataclasses import dataclass
from datetime import datetime
from typing import NewType
from uuid import UUID


from app.domain.value.email import Email


BaseId = NewType("BaseId", UUID)


@dataclass(eq=False, kw_only=True)
class BaseEntity(ABC):
    oid: BaseId

    def __eq__(self, other) -> bool:
        if isinstance(other, BaseId):
            return other.oid == self.oid
        return False

    def __hash__(self):
        return hash(self.oid)


@dataclass(eq=False, kw_only=True)
class User(BaseEntity):
    email: Email
    is_active: bool = True
    is_superuser: bool = False
    is_verified: bool = False
    create_at: datetime  # поле парситься поэтому не стоит его автоматически задавать


@dataclass(eq=False, kw_only=True)
class Description(BaseEntity):
    user_id:BaseId
    username: str
    phone: str

# Требуется агрегат из-за пересечения
@dataclass(eq=False, kw_only=True)
class Free_user_timing(BaseEntity):
    user_id: BaseId
    start_time: datetime
    end_time: datetime
