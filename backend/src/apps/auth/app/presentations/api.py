from typing import Annotated
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm


from app.presentations.dependens import AuthDep
from app.presentations.schemas import CreateUser, ResponseUser, TokenResponse


router = APIRouter(tags=["auth"])


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


# Не работает нужно передать uuid
@router.post(
    "/registry", summary="Регистрация пользователя.", response_model=ResponseUser
)
async def regesry_user(user_form: CreateUser, authser: AuthDep) -> ResponseUser:
    data = await authser.register(
        user_form.email, user_form.password, username=user_form.username
    )
    return ResponseUser(**data)


@router.post(
    "/login",
    summary="Пользователь логинится",
    status_code=200,
    description="Получение токенов авторизации",
    response_model=TokenResponse,
)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()], authser: AuthDep
) -> TokenResponse:

    tokens = await authser.login(form.username, form.password)
    return TokenResponse(access_token=tokens[0])

