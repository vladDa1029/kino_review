from dataclasses import dataclass

from app.application.errors.errors import EntityNotFoundError, UserNotFoundError
from app.application.ports.repositories import DescriptionRepository, UserRepository
from app.domain.entity.base import BaseId, Description
from app.domain.policy.description import DescriptionOwnershipPolicy


@dataclass(frozen=True, slots=True, kw_only=True)
class GetDescriptionQuery:
    user_id: BaseId


class GetDescriptionHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        description_repository: DescriptionRepository,
        ownership_policy: DescriptionOwnershipPolicy,
    ) -> None:
        self._user_repository = user_repository
        self._description_repository = description_repository
        self._ownership_policy = ownership_policy

    async def __call__(self, query: GetDescriptionQuery) -> Description:
        user = await self._user_repository.get(query.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")

        description = await self._description_repository.get_by_user_id(user.oid)
        if description is None:
            raise EntityNotFoundError("Description")

        self._ownership_policy.check(user, description)
        return description
