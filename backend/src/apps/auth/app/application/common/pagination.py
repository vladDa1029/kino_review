from dataclasses import dataclass
from typing import Dict, Final, Literal

from app.application.errors.query_param import PaginationError

MAX_PAGE_SIZE: Final[int] = 100


@dataclass(frozen=True, slots=True, kw_only=True)
class Pagination:
    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size

    def _validate_page(self) -> None:
        if self.page <= 0:
            raise PaginationError("Page number must be greater than 0.")

    def _validate_page_size(self):
        if self.page_size <= 0:
            raise PaginationError("Page size must be greater than 0.")
        if self.page_size > MAX_PAGE_SIZE:
            raise PaginationError(f"Page size must be not greate then {MAX_PAGE_SIZE}.")

    def __post_init__(self):
        self._validate_page()
        self._validate_page_size()

    def to_dict(self) -> Dict[Literal["page", "page_size"], int]:
        """Returns a dictionary representation of the page."""
        return dict(
            page=self.page,
            page_size=self.page_size,
        )
