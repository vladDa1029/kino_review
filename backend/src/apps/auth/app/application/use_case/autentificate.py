from typing import Optional


from app.application.use_case.exaptions import InvalidCredentialsExaption
from app.domain.entities import User
from app.domain.infrastruct import TransactionManager
from app.domain.use_case import AuthService
from app.infrastructure.adapters.repository import UserSqlAlchemyRepository
from app.infrastructure.security.jwt import JWTServices
from app.infrastructure.security.password_hasher import PasswordHasher


# Наследуемся от протокола и реализуем его
class JWTAuthServices(AuthService):
    def __init__(
        self,
        transaction_manager: TransactionManager,  # ← Протокол, не конкретная реализация
        password_hasher: PasswordHasher,  # ← Зависимость явно передаётся
        jwt_coder: JWTServices,  # ← Название лучше отражает суть
        user_repository: UserSqlAlchemyRepository,  # ← Добавляем репозиторий
    ) -> None:
        self._tm = transaction_manager
        self._hasher = password_hasher
        self._jwt = jwt_coder
        self._users = user_repository

    async def register(self, email: str, password: str, **data: dict) -> dict:
        if data.get("username", None) is None:
            raise ValueError("Не было переданно имя")
        user = User(
            username=data.get("username"),
            email=email,
            password=self._hasher.hash_password(password),
        )
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
