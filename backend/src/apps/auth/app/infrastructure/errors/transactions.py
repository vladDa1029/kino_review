from app.domain.errors.base import ApplicationError


class CommitError(ApplicationError):
    """Ошибка с commit"""


class RollbackError(ApplicationError):
    """Ошибка при откате"""
