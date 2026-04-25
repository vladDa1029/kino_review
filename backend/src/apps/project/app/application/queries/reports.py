from dataclasses import dataclass
from uuid import UUID

from app.application.ports.domain import (
    DocumentStoragePort,
    ProjectMemberRepository,
    ShiftReportRepository,
    ShiftRepository,
)
from app.application.support import get_actor_member, require_shift
from app.domain.entities import ShiftReport
from app.domain.enums import ShiftReportGenerationStatus
from app.domain.errors.business import EntityNotFoundError, StateTransitionError
from app.domain.policy import DirectorMemberPolicy


@dataclass(frozen=True, slots=True, kw_only=True)
class ListShiftReportsQuery:
    shift_id: UUID
    actor_user_id: UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class GetReportQuery:
    report_id: UUID
    actor_user_id: UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class GetReportDownloadUrlQuery:
    report_id: UUID
    actor_user_id: UUID


class ListShiftReportsHandler:
    def __init__(
        self,
        *,
        shift_reports: ShiftReportRepository,
        shifts: ShiftRepository,
        project_members: ProjectMemberRepository,
        director_member_policy: DirectorMemberPolicy,
    ) -> None:
        self._shift_reports = shift_reports
        self._shifts = shifts
        self._project_members = project_members
        self._director_member_policy = director_member_policy

    async def __call__(self, query: ListShiftReportsQuery) -> list[ShiftReport]:
        shift = await require_shift(shifts=self._shifts, shift_id=query.shift_id)
        actor = await get_actor_member(
            project_members=self._project_members,
            project_id=shift.project_id,
            user_id=query.actor_user_id,
        )
        self._director_member_policy.check(actor, action="read reports")
        return await self._shift_reports.list_by_shift(query.shift_id)


class GetReportHandler:
    def __init__(
        self,
        *,
        shift_reports: ShiftReportRepository,
        shifts: ShiftRepository,
        project_members: ProjectMemberRepository,
        director_member_policy: DirectorMemberPolicy,
    ) -> None:
        self._shift_reports = shift_reports
        self._shifts = shifts
        self._project_members = project_members
        self._director_member_policy = director_member_policy

    async def __call__(self, query: GetReportQuery) -> ShiftReport:
        report = await self._shift_reports.get_by_id(query.report_id)
        if report is None:
            raise EntityNotFoundError("Report is not found.")
        shift = await require_shift(shifts=self._shifts, shift_id=report.shift_id)
        actor = await get_actor_member(
            project_members=self._project_members,
            project_id=shift.project_id,
            user_id=query.actor_user_id,
        )
        self._director_member_policy.check(actor, action="read reports")
        return report


class GetReportDownloadUrlHandler:
    def __init__(
        self,
        *,
        shift_reports: ShiftReportRepository,
        shifts: ShiftRepository,
        project_members: ProjectMemberRepository,
        director_member_policy: DirectorMemberPolicy,
        document_storage: DocumentStoragePort,
    ) -> None:
        self._shift_reports = shift_reports
        self._shifts = shifts
        self._project_members = project_members
        self._director_member_policy = director_member_policy
        self._document_storage = document_storage

    async def __call__(self, query: GetReportDownloadUrlQuery) -> str:
        report = await self._shift_reports.get_by_id(query.report_id)
        if report is None:
            raise EntityNotFoundError("Report is not found.")
        shift = await require_shift(shifts=self._shifts, shift_id=report.shift_id)
        actor = await get_actor_member(
            project_members=self._project_members,
            project_id=shift.project_id,
            user_id=query.actor_user_id,
        )
        self._director_member_policy.check(actor, action="download reports")
        if report.generation_status != ShiftReportGenerationStatus.READY or not report.storage_key:
            raise StateTransitionError("Report is not ready for download.")
        return await self._document_storage.get_download_url(storage_key=report.storage_key)
