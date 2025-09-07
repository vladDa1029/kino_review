from typing import Annotated
from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Cookie, Depends, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from faststream.rabbit import RabbitBroker

from app.application.use_case.autentificate import JWTAuthServices
from app.presentations.schemas import (
    BrokerUserRegistered,
    CreateUser,
    ResponseUser,
    TokenResponse,
)
from app.infrastructure.adapters.broker import USER_REGISTERED_EXCHANGE

router = APIRouter(tags=["auth"], route_class=DishkaRoute)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


@router.post(
    "/register", summary="Регистрация пользователя.", response_model=ResponseUser
)
async def register_user(
    user_form: CreateUser,
    authser: FromDishka[JWTAuthServices],
    broker: FromDishka[RabbitBroker],
) -> ResponseUser:
    data = await authser.register(
        user_form.email,
        user_form.password,
    )
    event = BrokerUserRegistered(
        email=str(data.email),
        is_active=data.is_active,
        is_superuser=data.is_superuser,
        is_verified=data.is_verified,
        create_at=data.create_at,
    )
    await broker.publish(
        event, exchange=USER_REGISTERED_EXCHANGE, routing_key="user.registered"
    )
    return ResponseUser(
        email=str(data.email),
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
    response: Response,
) -> TokenResponse:

    tokens = await authser.login(form.username, form.password)

    response.set_cookie(
        key="refresh",
        value=tokens.get("refresh_token"),
        httponly=True,
        secure=False,
        samesite="strict",
        max_age=60 * 60 * 24 * 7,
    )
    token_resp = TokenResponse(access_token=tokens.get("access_token"))
    return token_resp


@router.post(
    "/refresh",
    summary="Обновление токенов.",
    status_code=200,
    response_model=TokenResponse,
)
async def refresh(
    response: Response,
    authser: FromDishka[JWTAuthServices],
    refresh_token: str = Cookie(alias="refresh"),
) -> TokenResponse:
    tokens = await authser.refresh_tokens(refresh_token)
    response.delete_cookie(
        "refresh",
        secure=False,
        samesite="strict",
    )
    response.set_cookie(  # может потребоваться вынисение в отдельную логику в будущем
        key="refresh",
        value=tokens.get("refresh_token"),
        httponly=True,
        secure=False,  # только HTTPS пока что не требуется, но стоит не забыть для продакшена (в теории)
        samesite="strict",  # или "lax", в зависимости от фронтенда надо будет узнать
        max_age=60 * 60 * 24 * 7,  # 7 дней
    )
    return TokenResponse(access_token=tokens.get("access_token"))


@router.get(
    "/logout",
    summary="Разлогинится пользователю.",
    description="Обнуление токенов. пока что только refresh.",
    status_code=200,
)
async def logout(response: Response, authser: FromDishka[JWTAuthServices]) -> str:
    response.delete_cookie(
        "refresh",
        secure=False,
        samesite="strict",
    )
    # await authser.logout()# вроде надо вызвать чтобы на будущее не забыть, но это черезмерно
    return "succesfull"
