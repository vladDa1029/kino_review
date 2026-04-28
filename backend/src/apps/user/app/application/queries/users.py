from dataclasses import dataclass
from uuid import UUID

from app.application.ports.repositories import UserRepository
from app.domain.entity.base import BaseId
from app.domain.value.email import Email


@dataclass(frozen=True, slots=True, kw_only=True)
class GetUserExistsQuery:
    user_id: BaseId


@dataclass(frozen=True, slots=True, kw_only=True)
class UserEmailLookupResult:
    user_id: UUID
    email: str


@dataclass(frozen=True, slots=True, kw_only=True)
class GetUserByEmailQuery:
    email: str


class GetUserExistsHandler:
    def __init__(self, user_repository: UserRepository) -> None:
        self._user_repository = user_repository

    async def __call__(self, query: GetUserExistsQuery) -> bool:
        return (await self._user_repository.get(query.user_id)) is not None


class GetUserByEmailHandler:
    def __init__(self, user_repository: UserRepository) -> None:
        self._user_repository = user_repository

    async def __call__(self, query: GetUserByEmailQuery) -> UserEmailLookupResult | None:
        user = await self._user_repository.get_by_email(Email(query.email.strip()))
        if user is None:
            return None
        return UserEmailLookupResult(user_id=user.oid, email=str(user.email))
