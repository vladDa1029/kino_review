# обработка разных ошибок

from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.application.errors.errors import (
    InvalidCredentialsError,
    UserAlreadyError,
)
from app.infrastructure.constants import (
    TOKEN_INVALID,
    TOKEN_SIGNATURE_INVALID,
    USER_ALREADY_EXISTS,
)
from app.infrastructure.errors.coder import NoValidTokenError


async def invalid_credentials_exaption_handler(
    request: Request, exc: InvalidCredentialsError
):
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"message": TOKEN_INVALID},
    )


async def no_valid_token_exaption_handler(request: Request, exc: NoValidTokenError):
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"message": TOKEN_SIGNATURE_INVALID},
    )


async def user_already_exists_exaption_handler(request: Request, exc: UserAlreadyError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"message": USER_ALREADY_EXISTS},
    )
