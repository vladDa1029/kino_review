from app.domain.errors.base import ApplicationError


class AvailabilityNotFoundError(ApplicationError):
    """No free window matches the requested interval."""


class ReservationOverlapError(ApplicationError):
    """Reservation overlaps an existing reserved segment."""


class WindowStatusError(ApplicationError):
    """Window status does not allow the operation."""
