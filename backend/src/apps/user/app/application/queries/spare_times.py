from dataclasses import dataclass

from app.application.errors.errors import EntityNotFoundError, UserNotFoundError
from app.application.ports.repositories import SpareTimeRepository, UserRepository
from app.domain.entity.base import BaseId, Spare_time
from app.domain.policy.ownership import OwnershipPolicy


@dataclass(frozen=True, slots=True, kw_only=True)
class ListUserSpareTimesQuery:
    user_id: BaseId


class ListUserSpareTimesHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        spare_time_repository: SpareTimeRepository,
    ) -> None:
        self._user_repository = user_repository
        self._spare_time_repository = spare_time_repository

    async def __call__(self, query: ListUserSpareTimesQuery) -> list[Spare_time]:
        user = await self._user_repository.get(query.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")
        return await self._spare_time_repository.list_by_obj_id(user.oid)


@dataclass(frozen=True, slots=True, kw_only=True)
class GetUserSpareTimeQuery:
    user_id: BaseId
    spare_time_id: BaseId


class GetUserSpareTimeHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        spare_time_repository: SpareTimeRepository,
        ownership_policy: OwnershipPolicy,
    ) -> None:
        self._user_repository = user_repository
        self._spare_time_repository = spare_time_repository
        self._ownership_policy = ownership_policy

    async def __call__(self, query: GetUserSpareTimeQuery) -> Spare_time:
        user = await self._user_repository.get(query.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")

        spare_time = await self._spare_time_repository.get(query.spare_time_id)
        if spare_time is None:
            raise EntityNotFoundError("Spare time")

        self._ownership_policy.check(user.oid, spare_time.obj)
        return spare_time
