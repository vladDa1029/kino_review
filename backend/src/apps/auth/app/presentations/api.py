from dataclasses import asdict
from typing import Annotated, List
from uuid import UUID
from pydantic import UUID4
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from app.config import get_settings
from app.presentations.dependens import JwtDep, UserUoWDep
from app.presentations.schemas import (
    CreateUsers,
    ResponseUsers,
    TokenResponse,
)


router = APIRouter(tags=["auth"])

settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


async def get_user_oid(
    token: Annotated[str, Depends(oauth2_scheme)], jwt: JwtDep
) -> UUID:
    """Извлекает UUID пользователя из JWT токена"""
    try:
        payload = jwt.decode_token(token)
        sub = payload.get("sub")
        if sub:
            # Преобразуем строку в UUID с проверкой типа
            if isinstance(sub, str):
                oid = UUID(sub)
            elif isinstance(sub, UUID):
                oid = sub
            else:
                raise ValueError("Invalid sub type in token")
            return oid
        else:
            raise jwt.InvalidTokenError("No sub field in token")
    except (jwt.InvalidTokenError, ValueError) as e:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("/login", response_model=TokenResponse, summary="User Login")
async def login(
    user_login: Annotated[OAuth2PasswordRequestForm, Depends()],
    uow: UserUoWDep,
    jwt: JwtDep,
):
    """Аутентификация пользователя и получение JWT токена"""
    async with uow:
        user = await uow.users.get_by_email(user_login.username)
        if user and uow.hasher.verify_password(user_login.password, user.password):
            token = jwt.create_token(str(user.oid), settings.auth.access_token_time)
            return TokenResponse(access_token=token)
    raise HTTPException(status_code=401, detail="Invalid credentials")


@router.post(
    "/user", status_code=201, response_model=ResponseUsers, summary="Create New User"
)
async def create_user(user: CreateUsers, uow: UserUoWDep):
    """Регистрация нового пользователя"""
    try:

        entity = user.from_entities()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    async with uow:
        old_user = await uow.users.get_by_email(entity.email)
        if not old_user:
            # Хэшируем пароль перед сохранением
            entity.password = uow.hasher.hash_password(entity.password)
            await uow.users.add(entity)
            user_data = asdict(entity)
            await uow.commit()
            return ResponseUsers.model_validate(user_data)
        else:
            raise HTTPException(
                status_code=400, detail="User with this email already exists"
            )


@router.get("/users", response_model=List[ResponseUsers], summary="Get All Users")
async def get_all_users(uow: UserUoWDep):
    """Получение списка всех пользователей (только для администраторов в будущем)"""
    async with uow:
        entities = await uow.users.list()
        users_data = [asdict(entity) for entity in entities]
        response = [ResponseUsers.model_validate(user) for user in users_data]
    return response


@router.get("/user", response_model=ResponseUsers, summary="Get Current User")
async def get_current_user(
    uow: UserUoWDep, oid: Annotated[UUID, Depends(get_user_oid)]
):
    """Получение данных текущего авторизованного пользователя"""
    async with uow:
        user_entity = await uow.users.get(oid)
        if not user_entity:
            raise HTTPException(status_code=404, detail="User not found")

        user_data = asdict(user_entity)
        # Убираем пароль из ответа для безопасности
        user_data.pop("password", None)
        response = ResponseUsers.model_validate(user_data)
    return response
