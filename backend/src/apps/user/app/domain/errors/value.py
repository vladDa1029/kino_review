from app.domain.errors.base import ApplicationError


class DomainFieldError(ApplicationError):
    """Ошибка при отусутствия полей в Value Object."""


class EmailError(ApplicationError):
    """Ошибка почта не валидна."""


class PhoneError(ApplicationError):
    """Ошибка телефон не валиден"""


class TimeRangeError(ApplicationError):
    """Invalid time range."""


class MinSpareTimeError(ApplicationError):
    """Time range is shorter than minimal duration."""


class AvailabilityStatusError(ApplicationError):
    """Availability status is invalid."""
