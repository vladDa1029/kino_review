from dataclasses import dataclass
from typing import Generic, TypeVar

from app.application.common.filters import EquipmentFilters
from app.application.common.pagination import Pagination
from app.application.common.sorting import EquipmentSorting
from app.application.ports.repositories import (
    CameraRepository,
    CameraTripodRepository,
    EquipmentRepository,
    LightRepository,
    LightTripodRepository,
    MicrofonRepository,
    RequisiteRepository,
    SoundRepository,
)
from app.domain.entity.base import (
    Camera,
    CameraTripod,
    Light,
    LightTripod,
    Microfon,
    Requisite,
    Sound,
)

TEquipment = TypeVar("TEquipment")


@dataclass(frozen=True, slots=True, kw_only=True)
class ListEquipmentQuery:
    filters: EquipmentFilters | None = None
    sorting: EquipmentSorting | None = None
    pagination: Pagination | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class EquipmentListResult(Generic[TEquipment]):
    items: list[TEquipment]
    total_count: int


class ListEquipmentHandler(Generic[TEquipment]):
    def __init__(self, repository: EquipmentRepository[TEquipment]) -> None:
        self._repository = repository

    async def __call__(
        self,
        query: ListEquipmentQuery,
    ) -> EquipmentListResult[TEquipment]:
        items = await self._repository.list(
            filters=query.filters,
            sorting=query.sorting,
            pagination=query.pagination,
        )
        total_count = await self._repository.count(filters=query.filters)
        return EquipmentListResult(items=items, total_count=total_count)


class ListMicrofonsHandler(ListEquipmentHandler[Microfon]):
    def __init__(self, repository: MicrofonRepository) -> None:
        super().__init__(repository)


class ListCamerasHandler(ListEquipmentHandler[Camera]):
    def __init__(self, repository: CameraRepository) -> None:
        super().__init__(repository)


class ListCameraTripodsHandler(ListEquipmentHandler[CameraTripod]):
    def __init__(self, repository: CameraTripodRepository) -> None:
        super().__init__(repository)


class ListLightsHandler(ListEquipmentHandler[Light]):
    def __init__(self, repository: LightRepository) -> None:
        super().__init__(repository)


class ListLightTripodsHandler(ListEquipmentHandler[LightTripod]):
    def __init__(self, repository: LightTripodRepository) -> None:
        super().__init__(repository)


class ListSoundsHandler(ListEquipmentHandler[Sound]):
    def __init__(self, repository: SoundRepository) -> None:
        super().__init__(repository)


class ListRequisitesHandler(ListEquipmentHandler[Requisite]):
    def __init__(self, repository: RequisiteRepository) -> None:
        super().__init__(repository)
