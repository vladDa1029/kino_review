from typing import Literal, Optional


from app.application.use_case.exceptions import (
    InvalidCredentialsExaption,
    UserAlreadyExistsExaption,
)
from app.domain.entities import User
from app.domain.exceptions.base import ApplicationExaption
from app.domain.infrastruct import TransactionManager
from app.domain.use_case import AuthService
from app.domain.values import Email
from app.infrastructure.adapters.repository import UserAbstractRepository
from app.infrastructure.generation import AbstractGenerationID
from app.infrastructure.security.jwt import JWTServices
from app.infrastructure.security.password_hasher import PasswordHasher


# Наследуемся от протокола и реализуем его
# Нужен транспорт для токенов и рефреш токенов который стоит выделит в отдельную сущность или не выводить так как рано
class JWTAuthServices(AuthService):
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

    # TODO: требуются кастомные ошибки: "такой аккаунт уже создан."
    async def register(self, email: str, password: str, **data: dict) -> User:
        if data.get("username", None) is None:
            raise ValueError("Не было переданно имя")

        user = User(
            oid=self.generation(),
            username=data.get("username"),
            email=Email(email),
            password=self._hasher.hash_password(password),
        )
        user_with_input_email = await self._users.get_by_email(str(user.email))
        if user_with_input_email:
            raise UserAlreadyExistsExaption()
        user_with_input_username = await self._users.get_by_username(str(user.username))
        if user_with_input_username:
            raise UserAlreadyExistsExaption()
        await self._users.add(user)
        await self._tm.commit()
        return user

    async def login(
        self, email: str, password: str
    ) -> dict[Literal["access_token", "refresh_token"], str]:
        user = await self._users.get_by_email(email=email)
        if not user:
            raise InvalidCredentialsExaption()
        if not self._hasher.verify_password(password, user.password):
            raise InvalidCredentialsExaption()
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
        if await self._users.get(user_oid) is None or payload.get("type") != "refresh":
            raise ApplicationExaption(
                message=f"Токен не валиден. oid : {user_oid}",
            )
        new_refresh_token = self._jwt.create_refresh_token(user_oid)
        access_token = self._jwt.create_access_token(user_oid)
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
        }

    async def logout(self, user_id: str, refresh_token: Optional[str] = None) -> None:
        pass
