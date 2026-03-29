import structlog
from fastapi import Request
from fastapi.responses import JSONResponse

from app.domain.errors.base import ApplicationError

log = structlog.get_logger(__file__)


async def application_error_handler(
    request: Request,
    exc: ApplicationError,
) -> JSONResponse:
    log.warning(
        "application.error",
        path=request.url.path,
        method=request.method,
        detail=str(exc),
    )
    return JSONResponse(status_code=400, content={"detail": str(exc)})
