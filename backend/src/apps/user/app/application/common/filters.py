from dataclasses import dataclass
from datetime import datetime

from app.application.errors.query_param import FilterError
from app.domain.entity.base import BaseId


@dataclass(frozen=True, slots=True, kw_only=True)
class EquipmentFilters:
    user_id: BaseId | None = None
    type: str | None = None
    size: str | None = None
    search: str | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None

    def __post_init__(self) -> None:
        if self.created_from and self.created_to:
            if self.created_from > self.created_to:
                raise FilterError("created_from must not be later than created_to.")

        if self.search is not None:
            normalized = self.search.strip()
            if not normalized:
                raise FilterError("search must not be empty.")
            object.__setattr__(self, "search", normalized)

        if self.type is not None:
            normalized = self.type.strip()
            if not normalized:
                raise FilterError("type must not be empty.")
            object.__setattr__(self, "type", normalized)

        if self.size is not None:
            normalized = self.size.strip()
            if not normalized:
                raise FilterError("size must not be empty.")
            object.__setattr__(self, "size", normalized)
