from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.application.ports.broker import EventPublisher
from app.application.ports.domain import (
    ClockPort,
    IdGeneratorPort,
    ProjectMemberRepository,
    ShiftRepository,
)
from app.application.ports.transaction import TransactionManager
from app.application.support import get_actor_member, publish_best_effort, require_shift
from app.domain.entities import Shift
from app.domain.services import ShiftService


@dataclass(frozen=True, slots=True, kw_only=True)
class CreateShiftCommand:
    project_id: UUID
    actor_user_id: UUID
    title: str
    description: str
    start_time: datetime
    end_time: datetime


class CreateShiftHandler:
    def __init__(
        self,
        *,
        transaction_manager: TransactionManager,
        clock: ClockPort,
        id_generator: IdGeneratorPort,
        publisher: EventPublisher,
        project_members: ProjectMemberRepository,
        shifts: ShiftRepository,
        shift_service: ShiftService,
    ) -> None:
        self._tx = transaction_manager
        self._clock = clock
        self._id_generator = id_generator
        self._publisher = publisher
        self._project_members = project_members
        self._shifts = shifts
        self._shift_service = shift_service

    async def __call__(self, command: CreateShiftCommand) -> Shift:
        now = self._clock.now()
        try:
            actor = await get_actor_member(
                project_members=self._project_members,
                project_id=command.project_id,
                user_id=command.actor_user_id,
            )
            shift = self._shift_service.create_shift(
                actor=actor,
                shift_id=self._id_generator(),
                project_id=command.project_id,
                title=command.title,
                description=command.description,
                start_time=command.start_time,
                end_time=command.end_time,
                now=now,
            )
            await self._shifts.add(shift)
            await self._tx.commit()
        except Exception:
            await self._tx.rollback()
            raise

        await publish_best_effort(
            publisher=self._publisher,
            topic="shift.created",
            payload={
                "project_id": str(command.project_id),
                "shift_id": str(shift.oid),
                "created_by": str(command.actor_user_id),
            },
        )
        return shift


@dataclass(frozen=True, slots=True, kw_only=True)
class ApproveShiftCommand:
    shift_id: UUID
    actor_user_id: UUID


class ApproveShiftHandler:
    def __init__(
        self,
        *,
        transaction_manager: TransactionManager,
        clock: ClockPort,
        publisher: EventPublisher,
        project_members: ProjectMemberRepository,
        shifts: ShiftRepository,
        shift_service: ShiftService,
    ) -> None:
        self._tx = transaction_manager
        self._clock = clock
        self._publisher = publisher
        self._project_members = project_members
        self._shifts = shifts
        self._shift_service = shift_service

    async def __call__(self, command: ApproveShiftCommand) -> Shift:
        now = self._clock.now()
        try:
            shift = await require_shift(shifts=self._shifts, shift_id=command.shift_id)
            actor = await get_actor_member(
                project_members=self._project_members,
                project_id=shift.project_id,
                user_id=command.actor_user_id,
            )
            self._shift_service.approve_shift(actor=actor, shift=shift, now=now)
            await self._shifts.update(shift)
            await self._tx.commit()
        except Exception:
            await self._tx.rollback()
            raise

        await publish_best_effort(
            publisher=self._publisher,
            topic="shift.approved",
            payload={
                "project_id": str(shift.project_id),
                "shift_id": str(shift.oid),
                "approved_by": str(command.actor_user_id),
            },
        )
        return shift
