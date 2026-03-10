from dataclasses import dataclass

from typing import ClassVar, Literal

from app.application.errors.query_param import SortingError


@dataclass(frozen=True, slots=True, kw_only=True)
class Sorting:
    field: str
    direction: Literal["asc", "desc"] = "asc"
    _allowed_fields: ClassVar[frozenset[str]] = frozenset(
        {"create_at", "is_active", "is_superuser", "is_verified"}
    )

    def __post_init__(self):
        if not self.field:
            raise SortingError("sort field is required.")
        if self.field not in self._allowed_fields:
            raise SortingError(
                f"sort field must be on of: {' '.join(self._allowed_fields)}."
            )
        if self.direction not in ("asc", "desc"):
            raise SortingError("sort directed must be 'asc' or 'desc'.")
