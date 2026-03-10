from app.domain.errors.base import ApplicationError


class PaginationError(ApplicationError):
    """The page is not valid."""


class FilterError(ApplicationError):
    """The Filter is not valid."""


class SortingError(ApplicationError):
    """The sorting is not valid."""
