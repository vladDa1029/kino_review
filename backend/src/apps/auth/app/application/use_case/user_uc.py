from collections.abc import Sequence
from dataclasses import dataclass

import structlog

from app.application.common.filters import Filter
from app.application.common.pagination import Pagination
from app.application.common.sorting import Sorting
from app.application.errors.errors import (
    AdminBlockedError,
    UserAlreadyError,
    UserNotFoundError,
)
from app.application.ports.transaction import TransactionManager
from app.domain.entities import User
from app.domain.values import Email
from app.infrastructure.adapters.repository import UserAbstractRepository
from app.infrastructure.generation import AbstractGenerationID
from app.infrastructure.security.password_hasher import PasswordHasher


log = structlog.get_logger(__file__)


@dataclass
class ListUserQuery:
    sorting: Sorting | None = None
    filters: Filter | None = None
    pagination: Pagination | None = None


class AdminUserService:
    def __init__(
        self,
        transaction_manager: TransactionManager,
        password_hasher: PasswordHasher,
        user_repository: UserAbstractRepository[User],
        generation: AbstractGenerationID,
    ) -> None:
        self._tm = transaction_manager
        self._hasher = password_hasher
        self._users = user_repository
        self._generation = generation

    async def create_user(
        self,
        email: str,
        password: str,
        *,
        is_active: bool = True,
        is_superuser: bool = False,
        is_verified: bool = False,
    ) -> User:
        self._ensure_admin_is_not_blocked(
            is_superuser=is_superuser,
            is_active=is_active,
        )
        user_email = Email(email)
        if await self._users.get_by_email(user_email):
            msg = f"User with email:{email} already exists"
            log.debug(msg)
            raise UserAlreadyError(msg)

        user = User(
            oid=self._generation(),
            email=user_email,
            password=self._hasher.hash_password(password),
            is_active=is_active,
            is_superuser=is_superuser,
            is_verified=is_verified,
        )
        await self._users.add(user)
        await self._tm.commit()
        return user

    async def get_user(self, user_id) -> User:
        user = await self._users.get(user_id)
        if user is None:
            msg = f"User with id:{user_id} not found"
            log.debug(msg)
            raise UserNotFoundError(msg)
        return user

    async def list_users(
        self,
        *,
        filters: Filter | None = None,
        sorting: Sorting | None = None,
        pagination: Pagination | None = None,
    ) -> Sequence[User]:
        return await self._users.list(
            filters=filters,
            sorting=sorting,
            pagination=pagination,
        )

    async def count_users(self, *, filters: Filter | None = None) -> int:
        return await self._users.count(filters=filters)

    async def update_user(
        self,
        user_id,
        *,
        email: str | None = None,
        password: str | None = None,
        is_active: bool | None = None,
        is_superuser: bool | None = None,
        is_verified: bool | None = None,
    ) -> User:
        user = await self.get_user(user_id)

        target_is_superuser = (
            user.is_superuser if is_superuser is None else is_superuser
        )
        target_is_active = user.is_active if is_active is None else is_active
        self._ensure_admin_is_not_blocked(
            is_superuser=target_is_superuser,
            is_active=target_is_active,
        )

        if email is not None and email != user.email.value:
            user_email = Email(email)
            existing_user = await self._users.get_by_email(user_email)
            if existing_user and existing_user.oid != user.oid:
                msg = f"User with email:{email} already exists"
                log.debug(msg)
                raise UserAlreadyError(msg)
            user.email = user_email

        if password is not None:
            user.password = self._hasher.hash_password(password)
        if is_active is not None:
            user.is_active = is_active
        if is_superuser is not None:
            user.is_superuser = is_superuser
        if is_verified is not None:
            user.is_verified = is_verified

        await self._tm.commit()
        return user

    async def delete_user(self, user_id) -> None:
        user = await self.get_user(user_id)
        await self._users.delete(user)
        await self._tm.commit()

    @staticmethod
    def _ensure_admin_is_not_blocked(*, is_superuser: bool, is_active: bool) -> None:
        if is_superuser and not is_active:
            raise AdminBlockedError("Admin user cannot be blocked.")
