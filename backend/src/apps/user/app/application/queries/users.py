from dataclasses import dataclass

from app.application.ports.repositories import UserRepository
from app.domain.entity.base import BaseId


@dataclass(frozen=True, slots=True, kw_only=True)
class GetUserExistsQuery:
    user_id: BaseId


class GetUserExistsHandler:
    def __init__(self, user_repository: UserRepository) -> None:
        self._user_repository = user_repository

    async def __call__(self, query: GetUserExistsQuery) -> bool:
        return (await self._user_repository.get(query.user_id)) is not None
