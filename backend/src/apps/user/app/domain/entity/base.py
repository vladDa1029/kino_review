from abc import ABC
from dataclasses import dataclass
from datetime import datetime
from typing import NewType
from uuid import UUID


from app.domain.value.email import Email
from app.domain.value.phone import Phone


BaseId = NewType("BaseId", UUID)


@dataclass(eq=False, kw_only=True)
class BaseEntity(ABC):
    oid: BaseId

    def __eq__(self, other) -> bool:
        if isinstance(other, BaseEntity):
            return self.oid == other.oid
        return False

    def __hash__(self):
        return hash(self.oid)


# WARN:  важно для этого сервиса : `is_active`, `is_superuser`, `is_verified`
@dataclass(eq=False, kw_only=True)
class User(BaseEntity):
    email: Email
    is_active: bool = True
    is_superuser: bool = False
    is_verified: bool = False
    create_at: datetime  # Поле парситься поэтому не стоит его автоматически задавать


@dataclass(eq=False, kw_only=True)
class Description(BaseEntity):
    user_id: BaseId
    username: str
    phone: Phone


# Требуется агрегат из-за пересечения
@dataclass(eq=False, kw_only=True)
class Spare_time(BaseEntity):
    """Сущность отвечающие за тип времени.

    Args:
        obj (BaseId): id объекта к которуму привязано время.
        start_time (datetime): начало периода.
        end_time (datetime): конец периода.
    """

    obj: BaseId
    start_time: datetime
    end_time: datetime
