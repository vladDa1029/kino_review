from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.application.errors.errors import EntityNotFoundError, UserNotFoundError
from app.domain.errors.availability import (
    AvailabilityNotFoundError,
    ReservationOverlapError,
    WindowStatusError,
)
from app.domain.errors.base import ApplicationError
from app.domain.errors.policy import (
    DescriptionAlreadyExistsError,
    DescriptionIdentityError,
    DescriptionOwnershipError,
    ImageOwnershipError,
    OwnershipError,
    ResourceLockedError,
    UserInactiveError,
)
from app.infrastructure.errors.transactions import CommitError, RollbackError

NOT_FOUND_ERRORS = (
    UserNotFoundError,
    EntityNotFoundError,
    AvailabilityNotFoundError,
)
FORBIDDEN_ERRORS = (
    UserInactiveError,
    OwnershipError,
    DescriptionOwnershipError,
    ImageOwnershipError,
)
CONFLICT_ERRORS = (
    DescriptionAlreadyExistsError,
    DescriptionIdentityError,
    ResourceLockedError,
    ReservationOverlapError,
    WindowStatusError,
)
SERVER_ERRORS = (CommitError, RollbackError)


async def application_error_handler(
    request: Request,
    exc: ApplicationError,
) -> JSONResponse:
    status_code = status.HTTP_400_BAD_REQUEST
    if isinstance(exc, NOT_FOUND_ERRORS):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, FORBIDDEN_ERRORS):
        status_code = status.HTTP_403_FORBIDDEN
    elif isinstance(exc, CONFLICT_ERRORS):
        status_code = status.HTTP_409_CONFLICT
    elif isinstance(exc, SERVER_ERRORS):
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return JSONResponse(
        status_code=status_code,
        content={"message": str(exc)},
    )
