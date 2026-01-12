from app.domain.errors.base import ApplicationError


class NoBaseIdeqError(ApplicationError):
    """OID должны совпадать"""


class CrossingTimingError(ApplicationError):
    """Время уже присутствует в сети (есть пересечение)."""
