import structlog
from fastapi import Request
from fastapi.responses import JSONResponse

from app.domain.errors.base import ApplicationError
from app.domain.errors.business import (
    AccessDeniedError,
    EntityNotFoundError,
    ExternalServiceError,
    StateTransitionError,
)

log = structlog.get_logger(__file__)


async def application_error_handler(
    request: Request,
    exc: ApplicationError,
) -> JSONResponse:
    status_code = 400
    if isinstance(exc, AccessDeniedError):
        status_code = 403
    elif isinstance(exc, EntityNotFoundError):
        status_code = 404
    elif isinstance(exc, StateTransitionError):
        status_code = 409
    elif isinstance(exc, ExternalServiceError):
        status_code = 502
    log.warning(
        "application.error",
        path=request.url.path,
        method=request.method,
        status_code=status_code,
        error_type=exc.__class__.__name__,
        detail=str(exc),
    )
    return JSONResponse(status_code=status_code, content={"detail": str(exc)})
