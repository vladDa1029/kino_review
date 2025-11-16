from app.domain.exceptions.base import ApplicationError


class NoValidTokenError(ApplicationError):
    """No valid token"""