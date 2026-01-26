from app.domain.errors.base import ApplicationError


class CommitError(ApplicationError):
    """Error during commit."""


class RollbackError(ApplicationError):
    """Error during rollback."""
