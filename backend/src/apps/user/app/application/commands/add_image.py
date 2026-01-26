from dataclasses import dataclass
from datetime import datetime

from app.application.errors.errors import EntityNotFoundError, UserNotFoundError
from app.application.ports.repositories import (
    ImageRepository,
    RequisiteRepository,
    UserRepository,
)
from app.application.ports.transaction import TransactionManager
from app.domain.entity.base import BaseId, Image
from app.domain.service.image_service import ImageService
from app.infrastructure.generation import AbstractGenerationID


@dataclass(frozen=True, slots=True, kw_only=True)
class AddImageCommand:
    user_id: BaseId
    requisite_id: BaseId
    file: str
    title: str
    storage_key: str
    bucket: str
    mime_type: str
    size: int
    description: str


class AddImageHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        requisite_repository: RequisiteRepository,
        image_repository: ImageRepository,
        transaction: TransactionManager,
        id_generator: AbstractGenerationID,
        service: ImageService,
    ) -> None:
        self._user_repository = user_repository
        self._requisite_repository = requisite_repository
        self._image_repository = image_repository
        self._transaction = transaction
        self._id_generator = id_generator
        self._service = service

    async def __call__(self, command: AddImageCommand) -> None:
        user = await self._user_repository.get(command.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")

        requisite = await self._requisite_repository.get(command.requisite_id)
        if requisite is None:
            raise EntityNotFoundError("Requisite")

        images = await self._image_repository.list_by_requisite_id(requisite.oid)

        image = Image(
            oid=self._id_generator(),
            requisite_id=requisite.oid,
            file=command.file,
            title=command.title,
            storage_key=command.storage_key,
            bucket=command.bucket,
            mime_type=command.mime_type,
            size=command.size,
            description=command.description,
            create_at=datetime.now(),
        )

        try:
            self._service.add_image(user, requisite, images, image)
            await self._image_repository.add(image)
            await self._transaction.commit()
        except Exception:
            await self._transaction.rollback()
            raise
