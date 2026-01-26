from dataclasses import dataclass
from datetime import datetime

from app.application.errors.errors import UserNotFoundError
from app.application.ports.repositories import MicrofonRepository, UserRepository
from app.application.ports.transaction import TransactionManager
from app.domain.entity.base import BaseId, Microfon
from app.domain.service.equipment_service import EquipmentService
from app.infrastructure.generation import AbstractGenerationID


@dataclass(frozen=True, slots=True, kw_only=True)
class CreateMicrofonCommand:
    user_id: BaseId
    title: str
    description: str
    type: str


class CreateMicrofonHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        microfon_repository: MicrofonRepository,
        transaction: TransactionManager,
        id_generator: AbstractGenerationID,
        service: EquipmentService,
    ) -> None:
        self._user_repository = user_repository
        self._microfon_repository = microfon_repository
        self._transaction = transaction
        self._id_generator = id_generator
        self._service = service

    async def __call__(self, command: CreateMicrofonCommand) -> None:
        user = await self._user_repository.get(command.user_id)
        if user is None:
            raise UserNotFoundError("User not found.")

        equipment = Microfon(
            oid=self._id_generator(),
            users_id=user.oid,
            title=command.title,
            description=command.description,
            type=command.type,
            create_at=datetime.now(),
        )

        try:
            self._service.create(user, equipment)
            await self._microfon_repository.add(equipment)
            await self._transaction.commit()
        except Exception:
            await self._transaction.rollback()
            raise
