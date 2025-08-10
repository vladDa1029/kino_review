from typing import Optional


from app.application.use_case.exaptions import InvalidCredentialsExaption, UserAlreadyExistsExaption
from app.domain.entities import User
from app.domain.infrastruct import TransactionManager
from app.domain.use_case import AuthService
from app.infrastructure.adapters.repository import UserAbstractRepository
from app.infrastructure.generation import AbstractGenerationID
from app.infrastructure.security.jwt import JWTServices
from app.infrastructure.security.password_hasher import PasswordHasher


# Наследуемся от протокола и реализуем его
class JWTAuthServices(AuthService):
    def __init__(
        self,
        transaction_manager: TransactionManager,  # ← Протокол, не конкретная реализация
        password_hasher: PasswordHasher,  # ← Зависимость явно передаётся
        jwt_coder: JWTServices,  # ← Название лучше отражает суть
        user_repository: UserAbstractRepository,  # ← Добавляем репозиторий
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
            email=email,
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

    async def login(self, email: str, password: str) -> dict[str, str]:
        user = await self._users.get_by_email(email=email)
        if not user:
            raise InvalidCredentialsExaption()
        if not self._hasher.verify_password(password, user.password):
            raise InvalidCredentialsExaption()
        access_token = self._jwt.create_access_token(sub=str(user.oid))
        return {"access_token": access_token}

    async def refresh_tokens(self, refresh_token: str) -> dict[str, str]:
        pass

    async def logout(self, user_id: str, refresh_token: Optional[str] = None) -> None:
        pass
