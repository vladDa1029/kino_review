from typing import Protocol

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


class UserRepository(Repository[User], Protocol):
    """User repository port."""


class DescriptionRepository(Repository[Description], Protocol):
    """Description repository port."""

    async def get_by_user_id(self, user_id: BaseId) -> Description | None:
        raise NotImplementedError


class SpareTimeRepository(Repository[Spare_time], Protocol):
    """Spare time repository port."""

    async def list_by_obj_id(self, obj_id: BaseId) -> list[Spare_time]:
        raise NotImplementedError


class MicrofonRepository(Repository[Microfon], Protocol):
    """Microfon repository port."""


class CameraRepository(Repository[Camera], Protocol):
    """Camera repository port."""


class CameraTripodRepository(Repository[CameraTripod], Protocol):
    """Camera tripod repository port."""


class LightRepository(Repository[Light], Protocol):
    """Light repository port."""


class LightTripodRepository(Repository[LightTripod], Protocol):
    """Light tripod repository port."""


class SoundRepository(Repository[Sound], Protocol):
    """Sound repository port."""


class RequisiteRepository(Repository[Requisite], Protocol):
    """Requisite repository port."""


class ImageRepository(Repository[Image], Protocol):
    """Image repository port."""

    async def list_by_requisite_id(self, requisite_id: BaseId) -> list[Image]:
        raise NotImplementedError
