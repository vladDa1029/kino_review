# обработка разных ошибок

from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.application.errors.errors import (
    AccessDeniedError,
    InvalidCredentialsError,
    PasswordOrLogInincorrectError,
    UserAlreadyError,
)
from app.infrastructure.constants import (
    PASSWORD_OR_LOGIN_INCORRECT,
    TOKEN_PERMISSION_DENIED,
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


async def password_or_login_incorrect_error_handler(
    request: Request, exc: PasswordOrLogInincorrectError
):
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"message": PASSWORD_OR_LOGIN_INCORRECT},
    )


async def access_denied_error_handler(request: Request, exc: AccessDeniedError):
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"message": TOKEN_PERMISSION_DENIED},
    )
