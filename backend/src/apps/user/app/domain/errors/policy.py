from app.domain.errors.base import ApplicationError


class UserInactiveError(ApplicationError):
    """User is inactive."""


class OwnershipError(ApplicationError):
    """Entity does not belong to owner."""


class DescriptionOwnershipError(ApplicationError):
    """Description does not belong to user."""


class DescriptionIdentityError(ApplicationError):
    """Description identity mismatch."""
