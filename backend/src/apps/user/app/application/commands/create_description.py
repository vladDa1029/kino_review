from dataclasses import dataclass

from app.application.errors.errors import UserNotFoundError
from app.application.ports.repositories import DescriptionRepository, UserRepository
from app.application.ports.transaction import TransactionManager
from app.domain.entity.base import BaseId, Description
from app.domain.service.description_service import DescriptionService
from app.domain.value.phone import Phone
from app.infrastructure.generation import AbstractGenerationID


@dataclass(frozen=True, slots=True, kw_only=True)
class CreateDescriptionCommand:
    user_id: BaseId
    username: str
    phone: str


class CreateDescriptionHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        description_repository: DescriptionRepository,
        transaction: TransactionManager,
        id_generator: AbstractGenerationID,
        service: DescriptionService,
    ) -> None:
        self._user_repository = user_repository
        self._description_repository = description_repository
        self._transaction = transaction
        self._id_generator = id_generator
        self._service = service

    async def __call__(self, command: CreateDescriptionCommand) -> None:
        user = await self._user_repository.get(command.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")

        existing = await self._description_repository.get_by_user_id(user.oid)

        description = Description(
            oid=self._id_generator(),
            user_id=user.oid,
            username=command.username,
            phone=Phone(command.phone),
        )

        try:
            self._service.create_description(user, existing, description)
            await self._description_repository.add(description)
            await self._transaction.commit()
        except Exception:
            await self._transaction.rollback()
            raise
