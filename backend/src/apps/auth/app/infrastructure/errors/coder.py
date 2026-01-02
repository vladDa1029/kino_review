from app.domain.errors.base import ApplicationError


class NoValidTokenError(ApplicationError):
    """No valid token"""
