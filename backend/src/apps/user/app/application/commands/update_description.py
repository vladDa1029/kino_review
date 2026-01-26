from dataclasses import dataclass

from app.application.errors.errors import EntityNotFoundError, UserNotFoundError
from app.application.ports.repositories import DescriptionRepository, UserRepository
from app.application.ports.transaction import TransactionManager
from app.domain.entity.base import BaseId, Description
from app.domain.service.description_service import DescriptionService
from app.domain.value.phone import Phone


@dataclass(frozen=True, slots=True, kw_only=True)
class UpdateDescriptionCommand:
    user_id: BaseId
    description_id: BaseId
    username: str
    phone: str


class UpdateDescriptionHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        description_repository: DescriptionRepository,
        transaction: TransactionManager,
        service: DescriptionService,
    ) -> None:
        self._user_repository = user_repository
        self._description_repository = description_repository
        self._transaction = transaction
        self._service = service

    async def __call__(self, command: UpdateDescriptionCommand) -> None:
        user = await self._user_repository.get(command.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")

        current = await self._description_repository.get(command.description_id)
        if current is None:
            raise EntityNotFoundError("Description")

        new_description = Description(
            oid=current.oid,
            user_id=current.user_id,
            username=command.username,
            phone=Phone(command.phone),
        )

        try:
            self._service.change_description(user, current, new_description)
            current.username = new_description.username
            current.phone = new_description.phone
            await self._description_repository.update(current)
            await self._transaction.commit()
        except Exception:
            await self._transaction.rollback()
            raise
