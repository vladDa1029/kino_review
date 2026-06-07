import math
from typing import Annotated
from uuid import UUID

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Cookie, Depends, Header, Response, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from faststream.rabbit import RabbitBroker

from app.application.common.filters import Filter
from app.application.common.pagination import Pagination
from app.application.common.sorting import Sorting
from app.application.errors.errors import InvalidCredentialsError
from app.application.queries.health import HealthHandler, HealthQuery
from app.application.use_case.authenticate_uc import JWTAuthServices
from app.application.use_case.user_uc import AdminUserService
from app.infrastructure.adapters.broker import USER_REGISTERED_EXCHANGE
from app.presentations.access import ensure_admin_headers
from app.presentations.schemas import (
    AdminUserCreateRequest,
    AdminUserUpdateRequest,
    BrokerUserRegistered,
    ListRequest,
    ListUsersGetResponse,
    TokenResponse,
    UserCreateRequest,
    UserGetForAdminResponse,
    UserGetResponse,
)

router = APIRouter(route_class=DishkaRoute)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


def _serialize_admin_user(user) -> UserGetForAdminResponse:
    return UserGetForAdminResponse(
        oid=str(user.oid),
        email=user.email.value,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        is_verified=user.is_verified,
    )


async def _publish_user_registered(user, broker: RabbitBroker) -> None:
    event = BrokerUserRegistered(
        user_id=str(user.oid),
        email=str(user.email),
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        is_verified=user.is_verified,
        create_at=user.create_at,
    )
    await broker.publish(
        event,
        exchange=USER_REGISTERED_EXCHANGE,
        routing_key="user.registered",
    )


@router.get(
    "/health",
    tags=["system"],
    summary="Health check",
    description="Returns a lightweight health payload for liveness and readiness probes.",
)
async def healthcheck(handler: FromDishka[HealthHandler]) -> dict:
    return await handler(HealthQuery())


def require_admin_access(
    x_user_token_type: Annotated[str | None, Header(alias="X-User-Token-Type")] = None,
    x_user_is_superuser: Annotated[str | None, Header(alias="X-User-Is-Superuser")] = None,
) -> None:
    ensure_admin_headers(
        x_user_token_type=x_user_token_type,
        x_user_is_superuser=x_user_is_superuser,
    )


@router.post(
    "/register",
    tags=["user"],
    summary="Register user",
    response_model=UserGetResponse,
)
async def register_user(
    user_form: UserCreateRequest,
    authser: FromDishka[JWTAuthServices],
    broker: FromDishka[RabbitBroker],
) -> UserGetResponse:
    data = await authser.register(
        user_form.email,
        user_form.password,
    )
    await _publish_user_registered(data, broker)
    return UserGetResponse(
        email=str(data.email),
        is_active=data.is_active,
        is_superuser=data.is_superuser,
        is_verified=data.is_verified,
    )


@router.post(
    "/login",
    tags=["user"],
    summary="Login user",
    status_code=200,
    description="Verify credentials and issue tokens.",
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
    return TokenResponse(access_token=tokens.get("access_token"))


@router.post(
    "/refresh",
    tags=["user"],
    summary="Refresh tokens",
    status_code=200,
    response_model=TokenResponse,
)
async def refresh(
    response: Response,
    authser: FromDishka[JWTAuthServices],
    refresh_token: str | None = Cookie(default=None, alias="refresh"),
) -> TokenResponse:
    if not refresh_token:
        raise InvalidCredentialsError(msg="Refresh token is missing.")
    tokens = await authser.refresh_tokens(refresh_token)
    response.delete_cookie(
        "refresh",
        secure=False,
        samesite="strict",
    )
    response.set_cookie(
        key="refresh",
        value=tokens.get("refresh_token"),
        httponly=True,
        secure=False,
        samesite="strict",
        max_age=60 * 60 * 24 * 7,
    )
    return TokenResponse(access_token=tokens.get("access_token"))


@router.get(
    "/logout",
    tags=["user"],
    summary="Logout user",
    description="Remove refresh token cookie on the client side.",
    status_code=200,
)
async def logout(response: Response, authser: FromDishka[JWTAuthServices]) -> str:
    response.delete_cookie(
        "refresh",
        secure=False,
        samesite="strict",
    )
    return "succesfull"


@router.post(
    "/admin/users",
    tags=["admin"],
    summary="Create user as admin",
    status_code=status.HTTP_201_CREATED,
    response_model=UserGetForAdminResponse,
)
async def create_admin_user(
    user_form: AdminUserCreateRequest,
    admin_service: FromDishka[AdminUserService],
    broker: FromDishka[RabbitBroker],
    _: None = Depends(require_admin_access),
) -> UserGetForAdminResponse:
    user = await admin_service.create_user(
        email=str(user_form.email),
        password=user_form.password,
        is_active=user_form.is_active,
        is_superuser=user_form.is_superuser,
        is_verified=user_form.is_verified,
    )
    await _publish_user_registered(user, broker)
    return _serialize_admin_user(user)


@router.get(
    "/admin/users",
    tags=["admin"],
    summary="List users for admin",
    status_code=200,
    response_model=ListUsersGetResponse,
)
async def get_users(
    admin_service: FromDishka[AdminUserService],
    param: ListRequest = Depends(),
    _: None = Depends(require_admin_access),
) -> ListUsersGetResponse:
    pagination = Pagination(
        page=param.page,
        page_size=param.page_size,
    )
    sorting = (
        None
        if param.sort_by is None
        else Sorting(
            field=param.sort_by,
            direction=param.sort_dir,
        )
    )
    filters = Filter(
        base_id=param.base_id,
        search=param.search,
        created_from=param.created_from,
        created_to=param.created_to,
    )

    users = await admin_service.list_users(
        filters=filters,
        pagination=pagination,
        sorting=sorting,
    )
    total_count = await admin_service.count_users(filters=filters)
    total_page = math.ceil(total_count / pagination.page_size)
    return ListUsersGetResponse(
        users=[_serialize_admin_user(user) for user in users],
        total_count=total_count,
        pages=total_page,
    )


@router.get(
    "/admin/users/{user_id}",
    tags=["admin"],
    summary="Get user for admin",
    response_model=UserGetForAdminResponse,
)
async def get_user_by_id(
    user_id: UUID,
    admin_service: FromDishka[AdminUserService],
    _: None = Depends(require_admin_access),
) -> UserGetForAdminResponse:
    user = await admin_service.get_user(user_id)
    return _serialize_admin_user(user)


@router.put(
    "/admin/users/{user_id}",
    tags=["admin"],
    summary="Update user for admin",
    response_model=UserGetForAdminResponse,
)
async def update_user_by_id(
    user_id: UUID,
    payload: AdminUserUpdateRequest,
    admin_service: FromDishka[AdminUserService],
    _: None = Depends(require_admin_access),
) -> UserGetForAdminResponse:
    user = await admin_service.update_user(
        user_id,
        email=str(payload.email) if payload.email is not None else None,
        password=payload.password,
        is_active=payload.is_active,
        is_superuser=payload.is_superuser,
        is_verified=payload.is_verified,
    )
    return _serialize_admin_user(user)


@router.delete(
    "/admin/users/{user_id}",
    tags=["admin"],
    summary="Delete user for admin",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_user_by_id(
    user_id: UUID,
    admin_service: FromDishka[AdminUserService],
    _: None = Depends(require_admin_access),
) -> Response:
    await admin_service.delete_user(user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
