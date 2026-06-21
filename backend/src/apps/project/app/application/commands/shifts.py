from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import structlog

from app.application.commands.reservation_outbox import (
    PARTICIPANT_CANCEL_OPERATION,
    RESOURCE_CANCEL_OPERATION,
    build_participant_cancel_request_id,
    build_resource_cancel_request_id,
    enqueue_reservation_message,
)
from app.application.commands.shift_reminders import (
    cancel_shift_reminder,
    upsert_shift_reminder,
)
from app.application.ports.broker import EventPublisher
from app.application.ports.domain import (
    ClockPort,
    IdGeneratorPort,
    ProjectMemberRepository,
    ReservationOutboxRepository,
    ResourceRequestRepository,
    ShiftParticipantRepository,
    ShiftReminderRepository,
    ShiftReportRepository,
    ShiftRepository,
)
from app.application.ports.tasks import (
    ScheduleShiftReportGenerationCommand,
    ShiftReportTaskDispatcher,
)
from app.application.ports.transaction import TransactionManager
from app.application.reports_support import (
    has_in_progress_report,
    mark_shift_reports_stale,
    next_shift_report_version,
)
from app.application.support import get_actor_member, publish_best_effort, require_shift
from app.config import ShiftReminder as ShiftReminderSettings
from app.domain.entities import Shift, ShiftReport
from app.domain.enums import (
    ResourceRequestStatus,
    ShiftParticipantStatus,
    ShiftReportActualityStatus,
    ShiftReportGenerationStatus,
)
from app.domain.errors.business import StateTransitionError
from app.domain.services import ResourceRequestService, ShiftParticipantService, ShiftService
from app.domain.specification.interval_within_shift import IntervalWithinShiftSpecification

log = structlog.get_logger(__name__)


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
        id_generator: IdGeneratorPort,
        publisher: EventPublisher,
        project_members: ProjectMemberRepository,
        shifts: ShiftRepository,
        shift_participants: ShiftParticipantRepository,
        resource_requests: ResourceRequestRepository,
        reservation_outbox: ReservationOutboxRepository,
        shift_reports: ShiftReportRepository,
        shift_reminders: ShiftReminderRepository,
        report_task_dispatcher: ShiftReportTaskDispatcher,
        shift_service: ShiftService,
        shift_participant_service: ShiftParticipantService,
        resource_request_service: ResourceRequestService,
        shift_reminder_settings: ShiftReminderSettings,
    ) -> None:
        self._tx = transaction_manager
        self._clock = clock
        self._id_generator = id_generator
        self._publisher = publisher
        self._project_members = project_members
        self._shifts = shifts
        self._shift_participants = shift_participants
        self._resource_requests = resource_requests
        self._reservation_outbox = reservation_outbox
        self._shift_reports = shift_reports
        self._shift_reminders = shift_reminders
        self._report_task_dispatcher = report_task_dispatcher
        self._shift_service = shift_service
        self._shift_participant_service = shift_participant_service
        self._resource_request_service = resource_request_service
        self._shift_reminder_settings = shift_reminder_settings

    async def __call__(self, command: ApproveShiftCommand) -> Shift:
        now = self._clock.now()
        report: ShiftReport | None = None
        try:
            shift = await require_shift(shifts=self._shifts, shift_id=command.shift_id)
            actor = await get_actor_member(
                project_members=self._project_members,
                project_id=shift.project_id,
                user_id=command.actor_user_id,
            )
            self._shift_service.approve_shift(actor=actor, shift=shift, now=now)
            await self._shifts.update(shift)

            # Only RESERVED participants/resources stay on an approved shift; cancel
            # everyone still awaiting a confirmation or reservation.
            await self._cancel_unsettled_participants(shift, now)
            await self._cancel_unsettled_resource_requests(shift, now)

            # Generate a fresh report for the now-locked shift composition.
            report = await self._create_report(shift, command.actor_user_id, now)

            await upsert_shift_reminder(
                shift_reminders=self._shift_reminders,
                clock=self._clock,
                id_generator=self._id_generator,
                settings=self._shift_reminder_settings,
                shift=shift,
            )
            await self._tx.commit()
        except Exception:
            await self._tx.rollback()
            raise

        if report is not None:
            await self._schedule_report_generation(report)

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

    async def _cancel_unsettled_participants(self, shift: Shift, now: datetime) -> None:
        for participant in await self._shift_participants.list_by_shift(shift.oid):
            needs_cancel = self._shift_participant_service.cancel_unsettled_on_approval(
                participant=participant,
                now=now,
            )
            await self._shift_participants.update(participant)
            if needs_cancel:
                await enqueue_reservation_message(
                    reservation_outbox=self._reservation_outbox,
                    clock=self._clock,
                    request_id=build_participant_cancel_request_id(participant.oid),
                    operation=PARTICIPANT_CANCEL_OPERATION,
                    aggregate_id=participant.oid,
                )

    async def _cancel_unsettled_resource_requests(self, shift: Shift, now: datetime) -> None:
        for request in await self._resource_requests.list_by_shift(shift.oid):
            needs_cancel = self._resource_request_service.cancel_unsettled_on_approval(
                request=request,
                now=now,
            )
            await self._resource_requests.update(request)
            if needs_cancel:
                await enqueue_reservation_message(
                    reservation_outbox=self._reservation_outbox,
                    clock=self._clock,
                    request_id=build_resource_cancel_request_id(request.oid),
                    operation=RESOURCE_CANCEL_OPERATION,
                    aggregate_id=request.oid,
                )

    async def _create_report(
        self,
        shift: Shift,
        actor_user_id: UUID,
        now: datetime,
    ) -> ShiftReport | None:
        existing_reports = await self._shift_reports.list_by_shift(shift.oid)
        if has_in_progress_report(existing_reports):
            return None
        report = ShiftReport(
            oid=self._id_generator(),
            project_id=shift.project_id,
            shift_id=shift.oid,
            version=next_shift_report_version(existing_reports),
            generation_status=ShiftReportGenerationStatus.PENDING,
            actuality_status=ShiftReportActualityStatus.ACTUAL,
            requested_by_user_id=actor_user_id,
            file_name=None,
            bucket=None,
            storage_key=None,
            mime_type=None,
            generated_at=None,
            archived_at=None,
            error_message=None,
            stale_reason=None,
            stale_marked_at=None,
            created_at=now,
            updated_at=now,
        )
        await self._shift_reports.add(report)
        return report

    async def _schedule_report_generation(self, report: ShiftReport) -> None:
        # Best effort: the shift is already approved, so a dispatch failure must not
        # roll the approval back. The report is left FAILED and can be regenerated.
        try:
            await self._report_task_dispatcher.schedule_generation(
                ScheduleShiftReportGenerationCommand(report_id=report.oid)
            )
        except Exception as exc:
            log.warning("shift.approve.report_dispatch_failed", report_id=str(report.oid), error=str(exc))
            report.generation_status = ShiftReportGenerationStatus.FAILED
            report.error_message = f"Task dispatch failed: {exc}"
            report.updated_at = self._clock.now()
            try:
                await self._shift_reports.update(report)
                await self._tx.commit()
            except Exception:
                await self._tx.rollback()


@dataclass(frozen=True, slots=True, kw_only=True)
class UpdateShiftCommand:
    shift_id: UUID
    actor_user_id: UUID
    title: str | None = None
    description: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None


class UpdateShiftHandler:
    def __init__(
        self,
        *,
        transaction_manager: TransactionManager,
        clock: ClockPort,
        publisher: EventPublisher,
        project_members: ProjectMemberRepository,
        shifts: ShiftRepository,
        shift_participants: ShiftParticipantRepository,
        resource_requests: ResourceRequestRepository,
        shift_service: ShiftService,
    ) -> None:
        self._tx = transaction_manager
        self._clock = clock
        self._publisher = publisher
        self._project_members = project_members
        self._shifts = shifts
        self._shift_participants = shift_participants
        self._resource_requests = resource_requests
        self._shift_service = shift_service
        self._interval_within_shift = IntervalWithinShiftSpecification()

    async def __call__(self, command: UpdateShiftCommand) -> Shift:
        now = self._clock.now()
        try:
            shift = await require_shift(shifts=self._shifts, shift_id=command.shift_id)
            actor = await get_actor_member(
                project_members=self._project_members,
                project_id=shift.project_id,
                user_id=command.actor_user_id,
            )
            title = command.title if command.title is not None else shift.title
            description = (
                command.description if command.description is not None else shift.description
            )
            start_time = command.start_time if command.start_time is not None else shift.start_time
            end_time = command.end_time if command.end_time is not None else shift.end_time
            self._shift_service.update_shift(
                actor=actor,
                shift=shift,
                title=title,
                description=description,
                start_time=start_time,
                end_time=end_time,
                now=now,
            )
            await self._ensure_existing_intervals_fit(shift)
            await self._shifts.update(shift)
            await self._tx.commit()
        except Exception:
            await self._tx.rollback()
            raise

        await publish_best_effort(
            publisher=self._publisher,
            topic="shift.updated",
            payload={
                "project_id": str(shift.project_id),
                "shift_id": str(shift.oid),
                "updated_by": str(command.actor_user_id),
            },
        )
        return shift

    async def _ensure_existing_intervals_fit(self, shift: Shift) -> None:
        participants = await self._shift_participants.list_by_shift(shift.oid)
        for participant in participants:
            if participant.status in {
                ShiftParticipantStatus.CANCELLED,
                ShiftParticipantStatus.DECLINED,
            }:
                continue
            if not self._interval_within_shift.is_satisfied(shift, participant.interval):
                raise StateTransitionError(
                    "Participant interval falls outside the new shift interval."
                )

        requests = await self._resource_requests.list_by_shift(shift.oid)
        for request in requests:
            if request.status in {
                ResourceRequestStatus.CANCELLED,
                ResourceRequestStatus.REJECTED_OWNER,
            }:
                continue
            if not self._interval_within_shift.is_satisfied(shift, request.interval):
                raise StateTransitionError(
                    "Resource request interval falls outside the new shift interval."
                )


@dataclass(frozen=True, slots=True, kw_only=True)
class CompleteShiftCommand:
    shift_id: UUID
    actor_user_id: UUID


class CompleteShiftHandler:
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

    async def __call__(self, command: CompleteShiftCommand) -> Shift:
        now = self._clock.now()
        try:
            shift = await require_shift(shifts=self._shifts, shift_id=command.shift_id)
            actor = await get_actor_member(
                project_members=self._project_members,
                project_id=shift.project_id,
                user_id=command.actor_user_id,
            )
            self._shift_service.complete_shift(actor=actor, shift=shift, now=now)
            await self._shifts.update(shift)
            await self._tx.commit()
        except Exception:
            await self._tx.rollback()
            raise

        await publish_best_effort(
            publisher=self._publisher,
            topic="shift.completed",
            payload={
                "project_id": str(shift.project_id),
                "shift_id": str(shift.oid),
                "completed_by": str(command.actor_user_id),
            },
        )
        return shift


@dataclass(frozen=True, slots=True, kw_only=True)
class CancelShiftCommand:
    shift_id: UUID
    actor_user_id: UUID
    reason: str | None = None


class CancelShiftHandler:
    def __init__(
        self,
        *,
        transaction_manager: TransactionManager,
        clock: ClockPort,
        publisher: EventPublisher,
        reservation_outbox: ReservationOutboxRepository,
        project_members: ProjectMemberRepository,
        shifts: ShiftRepository,
        shift_participants: ShiftParticipantRepository,
        resource_requests: ResourceRequestRepository,
        shift_reports: ShiftReportRepository,
        shift_reminders: ShiftReminderRepository,
        shift_service: ShiftService,
        shift_participant_service: ShiftParticipantService,
        resource_request_service: ResourceRequestService,
    ) -> None:
        self._tx = transaction_manager
        self._clock = clock
        self._publisher = publisher
        self._reservation_outbox = reservation_outbox
        self._project_members = project_members
        self._shifts = shifts
        self._shift_participants = shift_participants
        self._resource_requests = resource_requests
        self._shift_reports = shift_reports
        self._shift_reminders = shift_reminders
        self._shift_service = shift_service
        self._shift_participant_service = shift_participant_service
        self._resource_request_service = resource_request_service

    async def __call__(self, command: CancelShiftCommand) -> Shift:
        now = self._clock.now()
        try:
            shift = await require_shift(shifts=self._shifts, shift_id=command.shift_id)
            actor = await get_actor_member(
                project_members=self._project_members,
                project_id=shift.project_id,
                user_id=command.actor_user_id,
            )
            self._shift_service.cancel_shift(actor=actor, shift=shift, now=now)

            for participant in await self._shift_participants.list_by_shift(shift.oid):
                needs_cancel = self._shift_participant_service.cancel_due_to_shift(
                    participant=participant,
                    now=now,
                )
                await self._shift_participants.update(participant)
                if needs_cancel:
                    await enqueue_reservation_message(
                        reservation_outbox=self._reservation_outbox,
                        clock=self._clock,
                        request_id=build_participant_cancel_request_id(participant.oid),
                        operation=PARTICIPANT_CANCEL_OPERATION,
                        aggregate_id=participant.oid,
                    )

            for request in await self._resource_requests.list_by_shift(shift.oid):
                needs_cancel = self._resource_request_service.cancel_due_to_shift(
                    request=request,
                    now=now,
                )
                await self._resource_requests.update(request)
                if needs_cancel:
                    await enqueue_reservation_message(
                        reservation_outbox=self._reservation_outbox,
                        clock=self._clock,
                        request_id=build_resource_cancel_request_id(request.oid),
                        operation=RESOURCE_CANCEL_OPERATION,
                        aggregate_id=request.oid,
                    )

            await self._shifts.update(shift)
            await cancel_shift_reminder(
                shift_reminders=self._shift_reminders,
                clock=self._clock,
                shift_id=shift.oid,
            )
            await mark_shift_reports_stale(
                shift_reports=self._shift_reports,
                clock=self._clock,
                shift_id=shift.oid,
                reason="Shift was cancelled.",
            )
            await self._tx.commit()
        except Exception:
            await self._tx.rollback()
            raise

        await publish_best_effort(
            publisher=self._publisher,
            topic="shift.cancelled",
            payload={
                "project_id": str(shift.project_id),
                "shift_id": str(shift.oid),
                "cancelled_by": str(command.actor_user_id),
                "reason": command.reason,
            },
        )
        return shift
