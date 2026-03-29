from app.domain.errors.base import ApplicationError


class ConfirmationTokenInvalidError(ApplicationError):
    """Confirmation token is invalid."""


class ConfirmationTokenExpiredError(ApplicationError):
    """Confirmation token is expired."""
