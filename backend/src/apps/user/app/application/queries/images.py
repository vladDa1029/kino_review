from dataclasses import dataclass

from app.application.errors.errors import EntityNotFoundError, UserNotFoundError
from app.application.ports.repositories import (
    ImageRepository,
    RequisiteRepository,
    UserRepository,
)
from app.domain.entity.base import BaseId, Image
from app.domain.policy.image_ownership import ImageOwnershipPolicy
from app.domain.policy.ownership import OwnershipPolicy


@dataclass(frozen=True, slots=True, kw_only=True)
class ListRequisiteImagesQuery:
    user_id: BaseId
    requisite_id: BaseId


class ListRequisiteImagesHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        requisite_repository: RequisiteRepository,
        image_repository: ImageRepository,
        ownership_policy: OwnershipPolicy,
    ) -> None:
        self._user_repository = user_repository
        self._requisite_repository = requisite_repository
        self._image_repository = image_repository
        self._ownership_policy = ownership_policy

    async def __call__(self, query: ListRequisiteImagesQuery) -> list[Image]:
        user = await self._user_repository.get(query.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")

        requisite = await self._requisite_repository.get(query.requisite_id)
        if requisite is None:
            raise EntityNotFoundError("Requisite")

        self._ownership_policy.check(user.oid, requisite.users_id)

        return await self._image_repository.list_by_requisite_id(requisite.oid)


@dataclass(frozen=True, slots=True, kw_only=True)
class GetRequisiteImageQuery:
    user_id: BaseId
    requisite_id: BaseId
    image_id: BaseId


class GetRequisiteImageHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        requisite_repository: RequisiteRepository,
        image_repository: ImageRepository,
        ownership_policy: OwnershipPolicy,
        image_policy: ImageOwnershipPolicy,
    ) -> None:
        self._user_repository = user_repository
        self._requisite_repository = requisite_repository
        self._image_repository = image_repository
        self._ownership_policy = ownership_policy
        self._image_policy = image_policy

    async def __call__(self, query: GetRequisiteImageQuery) -> Image:
        user = await self._user_repository.get(query.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")

        requisite = await self._requisite_repository.get(query.requisite_id)
        if requisite is None:
            raise EntityNotFoundError("Requisite")

        image = await self._image_repository.get(query.image_id)
        if image is None:
            raise EntityNotFoundError("Image")

        self._ownership_policy.check(user.oid, requisite.users_id)
        self._image_policy.check(requisite, image)

        return image
