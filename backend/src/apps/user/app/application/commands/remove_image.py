from dataclasses import dataclass

from app.application.errors.errors import EntityNotFoundError, UserNotFoundError
from app.application.ports.repositories import (
    ImageRepository,
    RequisiteRepository,
    UserRepository,
)
from app.application.ports.transaction import TransactionManager
from app.domain.entity.base import BaseId
from app.domain.service.image_service import ImageService


@dataclass(frozen=True, slots=True, kw_only=True)
class RemoveImageCommand:
    user_id: BaseId
    requisite_id: BaseId
    image_id: BaseId


class RemoveImageHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        requisite_repository: RequisiteRepository,
        image_repository: ImageRepository,
        transaction: TransactionManager,
        service: ImageService,
    ) -> None:
        self._user_repository = user_repository
        self._requisite_repository = requisite_repository
        self._image_repository = image_repository
        self._transaction = transaction
        self._service = service

    async def __call__(self, command: RemoveImageCommand) -> None:
        user = await self._user_repository.get(command.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")

        requisite = await self._requisite_repository.get(command.requisite_id)
        if requisite is None:
            raise EntityNotFoundError("Requisite")

        image = await self._image_repository.get(command.image_id)
        if image is None:
            raise EntityNotFoundError("Image")

        images = await self._image_repository.list_by_requisite_id(requisite.oid)

        try:
            self._service.remove_image(user, requisite, images, image)
            await self._image_repository.delete(image)
            await self._transaction.commit()
        except Exception:
            await self._transaction.rollback()
            raise
