from dataclasses import dataclass
from datetime import UTC
from uuid import UUID

from app.application.ports.domain import (
    ClockPort,
    DocumentStoragePort,
    IdGeneratorPort,
    ProjectMemberRepository,
    ProjectRepository,
    ResourceRequestRepository,
    ShiftParticipantRepository,
    ShiftReportRepository,
    ShiftRepository,
)
from app.application.ports.reporting import (
    ShiftReportParticipantContext,
    ShiftReportRendererPort,
    ShiftReportResourceContext,
    ShiftReportSnapshotPort,
)
from app.application.ports.tasks import (
    ScheduleShiftReportGenerationCommand,
    ShiftReportTaskDispatcher,
)
from app.application.ports.transaction import TransactionManager
from app.application.reports_support import (
    REPORT_INCLUDED_PARTICIPANT_STATUSES,
    REPORT_INCLUDED_RESOURCE_STATUSES,
    has_in_progress_report,
    next_shift_report_version,
)
from app.application.support import get_actor_member, require_shift
from app.domain.entities import ShiftReport
from app.domain.enums import (
    ProjectRole,
    ResourceRequestStatus,
    ShiftParticipantStatus,
    ShiftReportActualityStatus,
    ShiftReportGenerationStatus,
    ShiftStatus,
)
from app.domain.errors.business import EntityNotFoundError, ExternalServiceError, StateTransitionError
from app.domain.policy import DirectorMemberPolicy


@dataclass(frozen=True, slots=True, kw_only=True)
class GenerateShiftReportCommand:
    shift_id: UUID
    actor_user_id: UUID


class GenerateShiftReportHandler:
    def __init__(
        self,
        *,
        transaction_manager: TransactionManager,
        clock: ClockPort,
        id_generator: IdGeneratorPort,
        project_members: ProjectMemberRepository,
        shifts: ShiftRepository,
        shift_reports: ShiftReportRepository,
        task_dispatcher: ShiftReportTaskDispatcher,
        director_member_policy: DirectorMemberPolicy,
    ) -> None:
        self._tx = transaction_manager
        self._clock = clock
        self._id_generator = id_generator
        self._project_members = project_members
        self._shifts = shifts
        self._shift_reports = shift_reports
        self._task_dispatcher = task_dispatcher
        self._director_member_policy = director_member_policy

    async def __call__(self, command: GenerateShiftReportCommand) -> ShiftReport:
        now = self._clock.now()
        shift = await require_shift(shifts=self._shifts, shift_id=command.shift_id)
        actor = await get_actor_member(
            project_members=self._project_members,
            project_id=shift.project_id,
            user_id=command.actor_user_id,
        )
        self._director_member_policy.check(actor, action="generate reports")
        if shift.status != ShiftStatus.APPROVED:
            raise StateTransitionError("Reports can be generated only for APPROVED shifts.")

        existing_reports = await self._shift_reports.list_by_shift(shift.oid)
        if has_in_progress_report(existing_reports):
            raise StateTransitionError("Shift already has a report generation in progress.")

        report = ShiftReport(
            oid=self._id_generator(),
            project_id=shift.project_id,
            shift_id=shift.oid,
            version=next_shift_report_version(existing_reports),
            generation_status=ShiftReportGenerationStatus.PENDING,
            actuality_status=ShiftReportActualityStatus.ACTUAL,
            requested_by_user_id=command.actor_user_id,
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

        try:
            await self._shift_reports.add(report)
            await self._tx.commit()
        except Exception:
            await self._tx.rollback()
            raise

        try:
            await self._task_dispatcher.schedule_generation(
                ScheduleShiftReportGenerationCommand(report_id=report.oid)
            )
        except Exception as exc:
            report.generation_status = ShiftReportGenerationStatus.FAILED
            report.error_message = f"Task dispatch failed: {exc}"
            report.updated_at = self._clock.now()
            try:
                await self._shift_reports.update(report)
                await self._tx.commit()
            except Exception:
                await self._tx.rollback()
                raise
            raise ExternalServiceError(f"Failed to schedule report generation: {exc}") from exc

        return report


@dataclass(frozen=True, slots=True, kw_only=True)
class ArchiveShiftReportCommand:
    report_id: UUID
    actor_user_id: UUID


class ArchiveShiftReportHandler:
    def __init__(
        self,
        *,
        transaction_manager: TransactionManager,
        clock: ClockPort,
        project_members: ProjectMemberRepository,
        shifts: ShiftRepository,
        shift_reports: ShiftReportRepository,
        director_member_policy: DirectorMemberPolicy,
    ) -> None:
        self._tx = transaction_manager
        self._clock = clock
        self._project_members = project_members
        self._shifts = shifts
        self._shift_reports = shift_reports
        self._director_member_policy = director_member_policy

    async def __call__(self, command: ArchiveShiftReportCommand) -> ShiftReport:
        report = await self._shift_reports.get_by_id(command.report_id)
        if report is None:
            raise EntityNotFoundError("Report is not found.")
        shift = await require_shift(shifts=self._shifts, shift_id=report.shift_id)
        actor = await get_actor_member(
            project_members=self._project_members,
            project_id=shift.project_id,
            user_id=command.actor_user_id,
        )
        self._director_member_policy.check(actor, action="archive reports")
        if report.generation_status in {
            ShiftReportGenerationStatus.PENDING,
            ShiftReportGenerationStatus.COLLECTING_SNAPSHOT,
            ShiftReportGenerationStatus.RENDERING,
        }:
            raise StateTransitionError("In-progress report cannot be archived.")
        if report.generation_status == ShiftReportGenerationStatus.ARCHIVED:
            raise StateTransitionError("Report is already archived.")

        now = self._clock.now()
        try:
            report.generation_status = ShiftReportGenerationStatus.ARCHIVED
            report.archived_at = now
            report.updated_at = now
            await self._shift_reports.update(report)
            await self._tx.commit()
        except Exception:
            await self._tx.rollback()
            raise
        return report


@dataclass(frozen=True, slots=True, kw_only=True)
class ProcessShiftReportGenerationCommand:
    report_id: UUID


class ProcessShiftReportGenerationHandler:
    def __init__(
        self,
        *,
        transaction_manager: TransactionManager,
        clock: ClockPort,
        projects: ProjectRepository,
        project_members: ProjectMemberRepository,
        shifts: ShiftRepository,
        shift_participants: ShiftParticipantRepository,
        resource_requests: ResourceRequestRepository,
        shift_reports: ShiftReportRepository,
        shift_report_snapshot: ShiftReportSnapshotPort,
        report_renderer: ShiftReportRendererPort,
        document_storage: DocumentStoragePort,
        snapshot_retry_count: int,
        snapshot_retry_delay_seconds: float,
    ) -> None:
        self._tx = transaction_manager
        self._clock = clock
        self._projects = projects
        self._project_members = project_members
        self._shifts = shifts
        self._shift_participants = shift_participants
        self._resource_requests = resource_requests
        self._shift_reports = shift_reports
        self._shift_report_snapshot = shift_report_snapshot
        self._report_renderer = report_renderer
        self._document_storage = document_storage
        self._snapshot_retry_count = snapshot_retry_count
        self._snapshot_retry_delay_seconds = snapshot_retry_delay_seconds

    async def __call__(self, command: ProcessShiftReportGenerationCommand) -> None:
        report = await self._shift_reports.get_by_id(command.report_id)
        if report is None:
            raise EntityNotFoundError("Report is not found.")
        if report.generation_status in {
            ShiftReportGenerationStatus.READY,
            ShiftReportGenerationStatus.ARCHIVED,
        }:
            return

        try:
            shift = await require_shift(shifts=self._shifts, shift_id=report.shift_id)
            project = await self._projects.get_by_id(report.project_id)
            if project is None:
                raise EntityNotFoundError("Project is not found.")

            await self._mark_collecting_snapshot(report)

            memberships = await self._project_members.list_by_project(report.project_id)
            memberships_by_user_id = {member.user_id: member for member in memberships}
            participant_context = tuple(
                ShiftReportParticipantContext(
                    participant_id=participant.oid,
                    user_id=participant.user_id,
                    project_role=_enum_name(
                        memberships_by_user_id.get(participant.user_id).role
                        if memberships_by_user_id.get(participant.user_id) is not None
                        else None,
                        fallback="UNKNOWN",
                    ),
                    shift_role=_enum_name(participant.role, fallback="UNKNOWN"),
                    time_from=participant.time_from,
                    time_to=participant.time_to,
                )
                for participant in await self._shift_participants.list_by_shift(report.shift_id)
                if _participant_status(participant) in REPORT_INCLUDED_PARTICIPANT_STATUSES
            )
            resource_context = tuple(
                ShiftReportResourceContext(
                    resource_request_id=request.oid,
                    resource_id=request.resource_id,
                    owner_user_id=request.resource_owner_user_id,
                    resource_type=request.resource_type,
                    time_from=request.time_from,
                    time_to=request.time_to,
                )
                for request in await self._resource_requests.list_by_shift(report.shift_id)
                if _resource_status(request) in REPORT_INCLUDED_RESOURCE_STATUSES
            )

            snapshot = await self._fetch_snapshot(
                report=report,
                participants=participant_context,
                resources=resource_context,
            )

            await self._mark_rendering(report)
            generated_at = self._clock.now()
            workbook = await self._report_renderer.render(
                report_id=report.oid,
                report_version=report.version,
                project_title=project.title,
                shift_title=shift.title,
                shift_start_time=shift.start_time,
                shift_end_time=shift.end_time,
                actuality_status=_report_actuality_status(report).name,
                generated_at=generated_at,
                participants=_build_participant_rows(
                    participants=participant_context,
                    snapshot=snapshot,
                ),
                owner_sections=_build_owner_sections(
                    participants=participant_context,
                    resources=resource_context,
                    snapshot=snapshot,
                ),
                external_owner_sections=_build_external_owner_sections(
                    participants=participant_context,
                    resources=resource_context,
                    snapshot=snapshot,
                ),
            )

            timestamp = generated_at.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
            file_name = f"shift-{shift.oid}-report-v{report.version}-{timestamp}.xlsx"
            storage_key = f"reports/{project.oid}/{shift.oid}/v{report.version}/{file_name}"
            stored = await self._document_storage.upload(
                filename=file_name,
                content=workbook,
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                storage_key=storage_key,
            )

            report.file_name = file_name
            report.bucket = stored.bucket
            report.storage_key = stored.storage_key
            report.mime_type = stored.mime_type
            report.generated_at = generated_at
            report.error_message = None
            report.generation_status = ShiftReportGenerationStatus.READY
            report.updated_at = self._clock.now()
            await self._shift_reports.update(report)
            await self._tx.commit()
        except Exception as exc:
            await self._mark_failed(report=report, reason=str(exc))

    async def _fetch_snapshot(
        self,
        *,
        report: ShiftReport,
        participants: tuple[ShiftReportParticipantContext, ...],
        resources: tuple[ShiftReportResourceContext, ...],
    ):
        last_exc: Exception | None = None
        for attempt in range(1, self._snapshot_retry_count + 1):
            try:
                return await self._shift_report_snapshot.fetch_snapshot(
                    report_id=report.oid,
                    project_id=report.project_id,
                    shift_id=report.shift_id,
                    participants=participants,
                    resources=resources,
                )
            except Exception as exc:  # noqa: PERF203
                last_exc = exc
                if attempt >= self._snapshot_retry_count:
                    break
                if self._snapshot_retry_delay_seconds > 0:
                    import asyncio

                    await asyncio.sleep(self._snapshot_retry_delay_seconds)
        raise ExternalServiceError(
            f"Report snapshot request failed after {self._snapshot_retry_count} attempt(s): {last_exc}"
        ) from last_exc

    async def _mark_collecting_snapshot(self, report: ShiftReport) -> None:
        report.generation_status = ShiftReportGenerationStatus.COLLECTING_SNAPSHOT
        report.error_message = None
        report.updated_at = self._clock.now()
        await self._shift_reports.update(report)
        await self._tx.commit()

    async def _mark_rendering(self, report: ShiftReport) -> None:
        report.generation_status = ShiftReportGenerationStatus.RENDERING
        report.updated_at = self._clock.now()
        await self._shift_reports.update(report)
        await self._tx.commit()

    async def _mark_failed(self, *, report: ShiftReport, reason: str) -> None:
        report.generation_status = ShiftReportGenerationStatus.FAILED
        report.error_message = reason
        report.updated_at = self._clock.now()
        try:
            await self._shift_reports.update(report)
            await self._tx.commit()
        except Exception:
            await self._tx.rollback()
            raise


def _participant_status(participant) -> ShiftParticipantStatus:
    value = participant.status
    if isinstance(value, ShiftParticipantStatus):
        return value
    return ShiftParticipantStatus(int(value))


def _resource_status(request) -> ResourceRequestStatus:
    value = request.status
    if isinstance(value, ResourceRequestStatus):
        return value
    return ResourceRequestStatus(int(value))


def _report_actuality_status(report) -> ShiftReportActualityStatus:
    value = report.actuality_status
    if isinstance(value, ShiftReportActualityStatus):
        return value
    return ShiftReportActualityStatus(int(value))


def _enum_name(value: object, *, fallback: str) -> str:
    if value is None:
        return fallback
    if hasattr(value, "name"):
        return str(getattr(value, "name"))
    if isinstance(value, int):
        try:
            return ProjectRole(int(value)).name
        except Exception:
            return fallback
    return str(value)


def _build_user_lookup(snapshot) -> dict[UUID, dict[str, str | None]]:
    return {
        user.user_id: {
            "username": user.username,
            "phone": user.phone,
            "email": user.email,
        }
        for user in snapshot.users
    }


def _build_resource_lookup(snapshot) -> dict[tuple[UUID, UUID], dict[str, str | None]]:
    return {
        (resource.resource_id, resource.owner_user_id): {
            "title": resource.title,
            "resource_type": resource.resource_type,
            "description": resource.description,
            "size": resource.size,
        }
        for resource in snapshot.resources
    }


def _build_participant_rows(*, participants, snapshot) -> tuple[dict[str, object], ...]:
    users = _build_user_lookup(snapshot)
    rows: list[dict[str, object]] = []
    for participant in participants:
        user = users.get(participant.user_id, {})
        rows.append(
            {
                "participant_id": participant.participant_id,
                "user_id": participant.user_id,
                "username": user.get("username") or "Неизвестный пользователь",
                "phone": user.get("phone") or "Телефон не указан",
                "email": user.get("email") or "Почта не указана",
                "project_role": participant.project_role,
                "shift_role": participant.shift_role,
                "time_from": participant.time_from,
                "time_to": participant.time_to,
            }
        )
    return tuple(rows)


def _build_owner_sections(*, participants, resources, snapshot) -> tuple[dict[str, object], ...]:
    users = _build_user_lookup(snapshot)
    resources_lookup = _build_resource_lookup(snapshot)
    participants_by_user_id = {participant.user_id: participant for participant in participants}
    sections: list[dict[str, object]] = []
    for participant in participants:
        items: list[dict[str, object]] = []
        for resource in resources:
            if resource.owner_user_id != participant.user_id:
                continue
            details = resources_lookup.get((resource.resource_id, resource.owner_user_id), {})
            items.append(
                {
                    "resource_request_id": resource.resource_request_id,
                    "resource_id": resource.resource_id,
                    "title": details.get("title") or "Неизвестный ресурс",
                    "type": details.get("resource_type") or resource.resource_type,
                    "description": details.get("description") or "Описание не указано",
                    "size": details.get("size"),
                    "owner_display_name": users.get(resource.owner_user_id, {}).get("username")
                    or "Неизвестный пользователь",
                    "time_from": resource.time_from,
                    "time_to": resource.time_to,
                }
            )
        sections.append(
            {
                "owner_user_id": participant.user_id,
                "owner_display_name": users.get(participant.user_id, {}).get("username")
                or "Неизвестный пользователь",
                "project_role": participant.project_role,
                "shift_role": participant.shift_role,
                "resources": tuple(items),
            }
        )
    return tuple(sections)


def _build_external_owner_sections(*, participants, resources, snapshot) -> tuple[dict[str, object], ...]:
    users = _build_user_lookup(snapshot)
    resources_lookup = _build_resource_lookup(snapshot)
    participant_user_ids = {participant.user_id for participant in participants}
    grouped: dict[UUID, list[dict[str, object]]] = {}
    for resource in resources:
        if resource.owner_user_id in participant_user_ids:
            continue
        details = resources_lookup.get((resource.resource_id, resource.owner_user_id), {})
        grouped.setdefault(resource.owner_user_id, []).append(
            {
                "resource_request_id": resource.resource_request_id,
                "resource_id": resource.resource_id,
                "title": details.get("title") or "Неизвестный ресурс",
                "type": details.get("resource_type") or resource.resource_type,
                "description": details.get("description") or "Описание не указано",
                "size": details.get("size"),
                "owner_display_name": users.get(resource.owner_user_id, {}).get("username")
                or "Неизвестный пользователь",
                "time_from": resource.time_from,
                "time_to": resource.time_to,
            }
        )

    sections = [
        {
            "owner_user_id": owner_user_id,
            "owner_display_name": users.get(owner_user_id, {}).get("username")
            or "Неизвестный пользователь",
            "resources": tuple(items),
        }
        for owner_user_id, items in grouped.items()
    ]
    sections.sort(key=lambda item: str(item["owner_display_name"]).lower())
    return tuple(sections)
