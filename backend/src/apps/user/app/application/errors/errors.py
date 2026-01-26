from app.domain.errors.base import ApplicationError


class UserNotFoundError(ApplicationError):
    """User not found."""


class EntityNotFoundError(ApplicationError):
    """Entity not found."""

    def __init__(self, entity: str) -> None:
        super().__init__(f"{entity} not found.")
