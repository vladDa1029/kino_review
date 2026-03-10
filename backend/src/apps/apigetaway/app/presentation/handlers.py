from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.application.errors import AccessDeniedError


async def access_denied_error_handler(
    request: Request,
    exc: AccessDeniedError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"detail": str(exc)},
    )
