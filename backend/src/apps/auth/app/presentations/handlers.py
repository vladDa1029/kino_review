# обработка разных ошибок

from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.application.use_case.exaptions import InvalidCredentialsExaption


async def invalid_credentials_exaption_handler(request: Request, exc : InvalidCredentialsExaption):
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"message": f"{exc.message}"},
    )