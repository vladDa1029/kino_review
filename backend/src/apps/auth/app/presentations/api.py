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
    LoginUser,
    ResponseUsers,
    TokenResponse,
)


router = APIRouter(tags=["auth"])

settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


async def get_user_oid(token: Annotated[str, Depends(oauth2_scheme)], jwt: JwtDep):
    try:
        payload = jwt.decode_token(token)
        sub = payload.get("sub")
        if sub:
            # Преобразуем строку в UUID
            oid = UUID(sub)  # или UUID(str(sub)) для гарантии строки
            return oid
        else:
            raise jwt.InvalidTokenError("No sub field in token")
    except (jwt.InvalidTokenError, ValueError) as e:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("/login", response_model=TokenResponse)
async def login(
    user_login: Annotated[OAuth2PasswordRequestForm, Depends()],
    uow: UserUoWDep,
    jwt: JwtDep,
):
    async with uow:
        user = await uow.users.get_by_email(user_login.username)
        if user:

            if uow.hasher.verify_password(user_login.password, user.password):
                token = jwt.create_token(str(user.oid), settings.auth.access_token_time)
                return TokenResponse(access_token=token)
    raise HTTPException(status_code=401, detail="Не правильная почта или пароль")


@router.post("/user")
async def create(user: CreateUsers, uow: UserUoWDep):

    try:
        entity = user.from_entities()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    async with uow:
        old_user = await uow.users.get_by_email(entity.email)
        if not old_user:
            entity.password = uow.hasher.hash_password(entity.password)
            await uow.users.add(entity)
            print(entity.password)
            await uow.commit()
        else:
            raise HTTPException(
                status_code=400, detail=f"Такой пользователь существует "
            )
    return {"msg": "succesfull"}


@router.get("/users", response_model=List[ResponseUsers])
async def list(uow: UserUoWDep):
    async with uow:
        entities = await uow.users.list()
        users_data = [asdict(entity) for entity in entities]
        response = [ResponseUsers.model_validate(user) for user in users_data]
    return response


@router.get("/user")
async def get(uow: UserUoWDep, oid: Annotated[str, Depends(get_user_oid)]):
    
    async with uow as uow:
        entities = await uow.users.get(oid)
        if not entities:
            raise HTTPException(status_code=404, detail="Page not found!")
        users_data = asdict(entities)
        response = ResponseUsers.model_validate(users_data)
    return response
