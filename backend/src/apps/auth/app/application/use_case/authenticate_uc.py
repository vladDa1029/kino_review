from typing import Literal, Optional
import structlog

from app.application.errors.errors import (
    InvalidCredentialsError,
    PasswordOrLogInincorrectError,
    UserAlreadyError,
)
from app.domain.entities import User
from app.application.ports.transaction import TransactionManager
from app.domain.values import Email
from app.infrastructure.adapters.repository import UserAbstractRepository
from app.infrastructure.generation import AbstractGenerationID
from app.infrastructure.security.jwt import JWTServices
from app.infrastructure.security.password_hasher import PasswordHasher

log = structlog.get_logger(__file__)


# Наследуемся от протокола и реализуем его
# Нужен транспорт для токенов и рефреш токенов который стоит выделит в отдельную сущность или не выводить так как рано
class JWTAuthServices:
    def __init__(
        self,
        transaction_manager: TransactionManager,  # Протокол
        password_hasher: PasswordHasher,  # Impl
        jwt_coder: JWTServices,  # Очент нужен интерейс не удобно разрабатывать
        user_repository: UserAbstractRepository,  # Интерфейс
        generation: AbstractGenerationID,
    ) -> None:
        self._tm = transaction_manager
        self._hasher = password_hasher
        self._jwt = jwt_coder
        self._users = user_repository
        self.generation = generation

    async def register(self, email: str, password: str, **data: dict) -> User:

        user = User(
            oid=self.generation(),
            email=Email(email),
            password=self._hasher.hash_password(password),
        )
        user_with_input_email = await self._users.get_by_email(user.email)
        if user_with_input_email:
            msg = f"User with email:{email} already exists"
            log.debug(msg)
            raise UserAlreadyError(msg)
        await self._users.add(user)
        await self._tm.commit()
        return user

    async def login(
        self, email: str, password: str
    ) -> dict[Literal["access_token", "refresh_token"], str]:
        valid_email = Email(email)
        user = await self._users.get_by_email(email=valid_email)
        if not user:
            msg = f"User with email:{email} no exists!"
            log.debug(msg)
            raise InvalidCredentialsError(msg)
        if not self._hasher.verify_password(password, user.password):
            msg = "Пароль должен совпадать."
            log.debug(msg)
            raise PasswordOrLogInincorrectError(msg)
        access_token = self._jwt.create_access_token(sub=str(user.oid))
        refresh_token = self._jwt.create_refresh_token(sub=str(user.oid))
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

    async def refresh_tokens(
        self, refresh_token: str
    ) -> dict[Literal["access_token", "refresh_token"], str]:
        payload = self._jwt.decode_token(refresh_token)
        user_oid = payload.get("sub")
        if payload.get("type") != "refresh":
            raise InvalidCredentialsError(
                msg=f"Токен не валиден.",
            )
        if await self._users.get(user_oid) is None:
            log.info(f"Подозрительный токен с user oid : {user_oid}")
            raise InvalidCredentialsError(
                msg=f"Токен не валиден.",
            )
        new_refresh_token = self._jwt.create_refresh_token(user_oid)
        access_token = self._jwt.create_access_token(user_oid)
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
        }

    async def logout(self, user_id: str, refresh_token: Optional[str] = None) -> None:
        pass
