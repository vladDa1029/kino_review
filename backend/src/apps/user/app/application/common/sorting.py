from dataclasses import dataclass
from typing import ClassVar, Literal

from app.application.errors.query_param import SortingError


@dataclass(frozen=True, slots=True, kw_only=True)
class EquipmentSorting:
    field: str
    direction: Literal["asc", "desc"] = "asc"

    allowed_fields: ClassVar[frozenset[str]] = frozenset(
        {"create_at", "title", "type", "size"}
    )

    def __post_init__(self) -> None:
        if not self.field:
            raise SortingError("sort field is required.")
        if self.field not in self.allowed_fields:
            raise SortingError(
                "sort field must be one of: create_at, title, type, size."
            )
        if self.direction not in ("asc", "desc"):
            raise SortingError("sort direction must be 'asc' or 'desc'.")
