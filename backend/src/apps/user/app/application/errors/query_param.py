from app.domain.errors.base import ApplicationError


class PaginationError(ApplicationError):
    """Invalid pagination parameters."""
