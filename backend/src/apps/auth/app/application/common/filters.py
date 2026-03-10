from dataclasses import dataclass
from datetime import datetime
from app.domain.entities import BaseUserId
from app.application.errors.query_param import FilterError


@dataclass(frozen=True, slots=True, kw_only=True)
class Filter:
    base_id: BaseUserId | None = None
    search: str | None = None
    created_to: datetime | None = None
    created_from: datetime | None = None

    def __post_init__(self) -> None:
        if self.created_from and self.created_to:
            if self.created_from > self.created_to:
                raise FilterError("created_from must be later than created_to.")

        if self.search is not None:
            normalized = self.search.strip()
            if not normalized:
                raise FilterError("search must not be empty.")
            object.__setattr__(self, "search", normalized)
