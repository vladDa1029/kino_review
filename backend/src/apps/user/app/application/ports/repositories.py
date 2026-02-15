from typing import Protocol, TypeVar

from app.application.common.filters import EquipmentFilters
from app.application.common.pagination import Pagination
from app.application.common.sorting import EquipmentSorting
from app.application.ports.repository import Repository
from app.domain.entity.base import (
    BaseId,
    Camera,
    CameraTripod,
    Description,
    Image,
    Light,
    LightTripod,
    Microfon,
    Requisite,
    Sound,
    Spare_time,
    User,
)
from app.domain.value.email import Email

TEquipment = TypeVar("TEquipment")


class UserRepository(Repository[User], Protocol):
    """User repository port."""

    async def get_by_email(self, email: Email) -> User | None:
        raise NotImplementedError


class DescriptionRepository(Repository[Description], Protocol):
    """Description repository port."""

    async def get_by_user_id(self, user_id: BaseId) -> Description | None:
        raise NotImplementedError


class FreeTimeRepository(Repository[Spare_time], Protocol):
    """Base free time repository port."""

    async def list_by_obj_id(self, obj_id: BaseId) -> list[Spare_time]:
        raise NotImplementedError


class SpareTimeRepository(FreeTimeRepository, Protocol):
    """User free time repository port."""


class MicrofonFreeTimeRepository(FreeTimeRepository, Protocol):
    """Microfon free time repository port."""


class CameraFreeTimeRepository(FreeTimeRepository, Protocol):
    """Camera free time repository port."""


class CameraTripodFreeTimeRepository(FreeTimeRepository, Protocol):
    """Camera tripod free time repository port."""


class LightFreeTimeRepository(FreeTimeRepository, Protocol):
    """Light free time repository port."""


class LightTripodFreeTimeRepository(FreeTimeRepository, Protocol):
    """Light tripod free time repository port."""


class SoundFreeTimeRepository(FreeTimeRepository, Protocol):
    """Sound free time repository port."""


class RequisiteFreeTimeRepository(FreeTimeRepository, Protocol):
    """Requisite free time repository port."""


class EquipmentRepository(Repository[TEquipment], Protocol):
    """Equipment repository port."""

    async def list(
        self,
        filters: EquipmentFilters | None = None,
        sorting: EquipmentSorting | None = None,
        pagination: Pagination | None = None,
    ) -> list[TEquipment]:
        raise NotImplementedError

    async def count(
        self,
        filters: EquipmentFilters | None = None,
    ) -> int:
        raise NotImplementedError


class MicrofonRepository(EquipmentRepository[Microfon], Protocol):
    """Microfon repository port."""


class CameraRepository(EquipmentRepository[Camera], Protocol):
    """Camera repository port."""


class CameraTripodRepository(EquipmentRepository[CameraTripod], Protocol):
    """Camera tripod repository port."""


class LightRepository(EquipmentRepository[Light], Protocol):
    """Light repository port."""


class LightTripodRepository(EquipmentRepository[LightTripod], Protocol):
    """Light tripod repository port."""


class SoundRepository(EquipmentRepository[Sound], Protocol):
    """Sound repository port."""


class RequisiteRepository(EquipmentRepository[Requisite], Protocol):
    """Requisite repository port."""


class ImageRepository(Repository[Image], Protocol):
    """Image repository port."""

    async def list_by_requisite_id(self, requisite_id: BaseId) -> list[Image]:
        raise NotImplementedError
