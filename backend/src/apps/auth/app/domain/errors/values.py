from app.domain.errors.base import ApplicationError


class DomainFieldError(ApplicationError):
    """Ошибка при отусутствия полей в Value Object."""


class EmailError(ApplicationError):
    """Ошибка почта не валидна."""
