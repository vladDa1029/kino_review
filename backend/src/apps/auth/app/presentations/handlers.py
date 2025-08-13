# обработка разных ошибок

from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.application.use_case.exaptions import (
    InvalidCredentialsExaption,
    UserAlreadyExistsExaption,
)
from app.infrastructure.exaptions.coder import NoValidTokenExption


async def invalid_credentials_exaption_handler(
    request: Request, exc: InvalidCredentialsExaption
):
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"message": f"{exc.message}"},
    )
async def no_valid_token_exaption_handler(request: Request, exc: NoValidTokenExption
):
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"message": f"Токен не валидный."},
    )

async def user_already_exists_exaption_handler(
    request: Request, exc: UserAlreadyExistsExaption
):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"message": f"{exc.message}"},
    )
