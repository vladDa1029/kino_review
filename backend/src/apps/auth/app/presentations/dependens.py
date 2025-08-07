from typing import Annotated, AsyncIterator
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.application.use_case.autentificate import JWTAuthServices
from app.config import Auth
from app.domain.infrastruct import TransactionManager
from app.domain.use_case import AuthService
from app.infrastructure.adapters.repository import (
    AbstractRepository,
    UserSqlAlchemyRepository,
)
from app.infrastructure.database import get_session
from app.infrastructure.security.jwt import JWTServices
from app.infrastructure.security.password_hasher import PasswordHasher
from app.infrastructure.transections import TransactionManagerAlchemy


def _get_jwt(request: Request) -> JWTServices:
    return request.app.state.jwt_service


def get_password_hasher() -> PasswordHasher:
    return PasswordHasher()


async def get_async_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.session_maker() as session:
        yield session

def _get_user_repository(
    session: AsyncSession = Depends(get_async_session),
) -> AbstractRepository:
    return UserSqlAlchemyRepository(session)


def _get_transaction_manager(
    session: AsyncSession = Depends(get_async_session),
) -> TransactionManager:
    return TransactionManagerAlchemy(session)


# Фабрика сервиса БЕЗ AsyncSession в параметрах
def get_auth_service(
    user_repository: AbstractRepository = Depends(_get_user_repository),
    transaction_manager: TransactionManager = Depends(_get_transaction_manager),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
    jwt_coder: JWTServices = Depends(_get_jwt),
) -> JWTAuthServices:
    return JWTAuthServices(
        user_repository=user_repository,
        transaction_manager=transaction_manager,
        password_hasher=password_hasher,
        jwt_coder=jwt_coder,
    )

AuthDep = Annotated[JWTAuthServices, Depends(get_auth_service)]