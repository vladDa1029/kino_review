from app.domain.errors.base import ApplicationError


class DomainError(ApplicationError):
    """Base domain error."""


class DomainInvariantError(DomainError):
    """Raised when domain invariant is violated."""


class AccessDeniedError(DomainError):
    """Raised when user does not have enough permissions."""


class EntityNotFoundError(DomainError):
    """Raised when entity is not found in business operation."""


class StateTransitionError(DomainError):
    """Raised when status/state transition is forbidden."""


class ExternalServiceError(DomainError):
    """Raised when external dependency call failed."""
