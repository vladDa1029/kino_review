from app.domain.errors.base import ApplicationError


class InvalidCredentialsError(ApplicationError):
    """Use-case credential validation error."""


class UserAlreadyError(ApplicationError):
    """Raised when a user with the same email already exists."""


class PasswordOrLogInincorrectError(ApplicationError):
    """Raised when email or password is invalid."""


class AccessDeniedError(ApplicationError):
    """Raised when the caller does not have enough permissions."""
