from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from typing import NewType
from uuid import UUID


from app.domain.value.email import Email
from app.domain.value.phone import Phone
from app.domain.value.status import AvailabilityStatus


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


# WARN: Не должно быть в сервисе `is_active`, `is_superuser`, `is_verified` так как это не его ответственность
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
    status: AvailabilityStatus = field(
        default_factory=lambda: AvailabilityStatus("free")
    )


@dataclass(eq=False, kw_only=True)
class AvailabilityReservation(BaseEntity):
    user_id: BaseId
    obj_id: BaseId
    start_time: datetime
    end_time: datetime
    reservation_id: BaseId
    created_at: datetime


@dataclass(eq=False, kw_only=True)
class Microfon(BaseEntity):
    users_id: BaseId
    title: str
    description: str
    type: str
    create_at: datetime


@dataclass(eq=False, kw_only=True)
class Camera(BaseEntity):
    users_id: BaseId
    title: str
    description: str
    type: str
    create_at: datetime


@dataclass(eq=False, kw_only=True)
class CameraTripod(BaseEntity):
    users_id: BaseId
    title: str
    description: str
    type: str
    create_at: datetime


@dataclass(eq=False, kw_only=True)
class Light(BaseEntity):
    users_id: BaseId
    title: str
    description: str
    type: str
    create_at: datetime


@dataclass(eq=False, kw_only=True)
class LightTripod(BaseEntity):
    users_id: BaseId
    title: str
    description: str
    type: str
    create_at: datetime


@dataclass(eq=False, kw_only=True)
class Sound(BaseEntity):
    users_id: BaseId
    title: str
    description: str
    type: str
    create_at: datetime


@dataclass(eq=False, kw_only=True)
class Requisite(BaseEntity):
    users_id: BaseId
    title: str
    description: str
    type: str
    size: str
    create_at: datetime


@dataclass(eq=False, kw_only=True)
class Image(BaseEntity):
    requisite_id: BaseId
    file: str
    title: str
    storage_key: str
    bucket: str
    mime_type: str
    size: int
    description: str
    create_at: datetime
