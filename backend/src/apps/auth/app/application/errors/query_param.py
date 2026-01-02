from app.domain.errors.base import ApplicationError


class PaginationError(ApplicationError):
    """The page is not valid."""
