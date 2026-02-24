from fastapi import Request
from fastapi.responses import JSONResponse

from app.domain.errors.base import ApplicationError


async def application_error_handler(
    request: Request,
    exc: ApplicationError,
) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})
