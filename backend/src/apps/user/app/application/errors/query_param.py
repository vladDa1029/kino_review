from app.domain.errors.base import ApplicationError


class PaginationError(ApplicationError):
    """Invalid pagination parameters."""


class FilterError(ApplicationError):
    """Invalid filter parameters."""


class SortingError(ApplicationError):
    """Invalid sorting parameters."""
