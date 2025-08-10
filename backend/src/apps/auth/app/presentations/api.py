from typing import Annotated
from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm


from app.application.use_case.autentificate import JWTAuthServices
from app.presentations.schemas import CreateUser, ResponseUser, TokenResponse


router = APIRouter(tags=["auth"], route_class=DishkaRoute)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


# Не работает нужно передать uuid
@router.post(
    "/registry", summary="Регистрация пользователя.", response_model=ResponseUser
)
async def regesry_user(
    user_form: CreateUser, authser: FromDishka[JWTAuthServices]
) -> ResponseUser:
    data = await authser.register(
        user_form.email, user_form.password, username=user_form.username
    )
    return ResponseUser(
        username=data.username,
        email=data.email,
        is_active=data.is_active,
        is_superuser=data.is_superuser,
        is_verified=data.is_verified,
    )


@router.post(
    "/login",
    summary="Пользователь логинится",
    status_code=200,
    description="Получение токенов авторизации",
    response_model=TokenResponse,
)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    authser: FromDishka[JWTAuthServices],
) -> TokenResponse:

    tokens = await authser.login(form.username, form.password)
    return TokenResponse(access_token=tokens.get("access_token"))
