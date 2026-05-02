from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.application.ports.domain import (
    DocumentRepository,
    DocumentStoragePort,
    ProjectMemberRepository,
    ProjectRepository,
    ShiftReportRepository,
    ShiftRepository,
)
from app.application.support import require_shift
from app.domain.entities import Document, Project, ShiftReport
from app.domain.enums import ShiftReportGenerationStatus
from app.domain.errors.business import EntityNotFoundError, StateTransitionError

@dataclass(frozen=True, slots=True, kw_only=True)
class ListAdminProjectsQuery:
    include_archived: bool = False


class ListAdminProjectsHandler:
    def __init__(self, *, projects: ProjectRepository) -> None:
        self._projects = projects

    async def __call__(self, query: ListAdminProjectsQuery) -> list[Project]:
        return await self._projects.list_all(include_archived=query.include_archived)


@dataclass(frozen=True, slots=True, kw_only=True)
class GetAdminProjectQuery:
    project_id: UUID


class GetAdminProjectHandler:
    def __init__(self, *, projects: ProjectRepository) -> None:
        self._projects = projects

    async def __call__(self, query: GetAdminProjectQuery) -> Project:
        project = await self._projects.get_by_id(query.project_id)
        if project is None:
            raise EntityNotFoundError("Project is not found.")
        return project


@dataclass(frozen=True, slots=True, kw_only=True)
class ListAdminProjectMembersQuery:
    project_id: UUID
    user_id: UUID | None = None
    include_inactive: bool = False


@dataclass(frozen=True, slots=True)
class AdminProjectMemberView:
    oid: UUID
    user_id: UUID
    role: int
    status: int
    invited_by: UUID
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class GetAdminProjectMemberQuery:
    project_id: UUID
    target_user_id: UUID
    include_inactive: bool = False


class ListAdminProjectMembersHandler:
    def __init__(
        self,
        *,
        projects: ProjectRepository,
        project_members: ProjectMemberRepository,
    ) -> None:
        self._projects = projects
        self._project_members = project_members

    async def __call__(self, query: ListAdminProjectMembersQuery) -> list[AdminProjectMemberView]:
        project = await self._projects.get_by_id(query.project_id)
        if project is None:
            raise EntityNotFoundError("Project is not found.")
        members = await self._project_members.list_by_project(query.project_id)
        return [
            AdminProjectMemberView(
                oid=member.oid,
                user_id=member.user_id,
                role=int(member.role),
                status=int(member.status),
                invited_by=member.invited_by,
                created_at=member.created_at,
                updated_at=member.updated_at,
            )
            for member in members
            if (query.include_inactive or member.is_active)
            and (query.user_id is None or member.user_id == query.user_id)
        ]


class GetAdminProjectMemberHandler:
    def __init__(
        self,
        *,
        projects: ProjectRepository,
        project_members: ProjectMemberRepository,
    ) -> None:
        self._projects = projects
        self._project_members = project_members

    async def __call__(self, query: GetAdminProjectMemberQuery) -> AdminProjectMemberView:
        project = await self._projects.get_by_id(query.project_id)
        if project is None:
            raise EntityNotFoundError("Project is not found.")
        member = await self._project_members.get_by_project_and_user(
            project_id=query.project_id,
            user_id=query.target_user_id,
        )
        if member is None or (not query.include_inactive and not member.is_active):
            raise EntityNotFoundError("Target member is not found in project.")
        return AdminProjectMemberView(
            oid=member.oid,
            user_id=member.user_id,
            role=int(member.role),
            status=int(member.status),
            invited_by=member.invited_by,
            created_at=member.created_at,
            updated_at=member.updated_at,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ListAdminShiftReportsQuery:
    shift_id: UUID


class ListAdminShiftReportsHandler:
    def __init__(
        self,
        *,
        shift_reports: ShiftReportRepository,
        shifts: ShiftRepository,
    ) -> None:
        self._shift_reports = shift_reports
        self._shifts = shifts

    async def __call__(self, query: ListAdminShiftReportsQuery) -> list[ShiftReport]:
        await require_shift(shifts=self._shifts, shift_id=query.shift_id)
        return await self._shift_reports.list_by_shift(query.shift_id)


@dataclass(frozen=True, slots=True, kw_only=True)
class GetAdminReportQuery:
    report_id: UUID


class GetAdminReportHandler:
    def __init__(self, *, shift_reports: ShiftReportRepository) -> None:
        self._shift_reports = shift_reports

    async def __call__(self, query: GetAdminReportQuery) -> ShiftReport:
        report = await self._shift_reports.get_by_id(query.report_id)
        if report is None:
            raise EntityNotFoundError("Report is not found.")
        return report


@dataclass(frozen=True, slots=True, kw_only=True)
class GetAdminReportDownloadUrlQuery:
    report_id: UUID


class GetAdminReportDownloadUrlHandler:
    def __init__(
        self,
        *,
        shift_reports: ShiftReportRepository,
        document_storage: DocumentStoragePort,
    ) -> None:
        self._shift_reports = shift_reports
        self._document_storage = document_storage

    async def __call__(self, query: GetAdminReportDownloadUrlQuery) -> str:
        report = await self._shift_reports.get_by_id(query.report_id)
        if report is None:
            raise EntityNotFoundError("Report is not found.")
        if report.generation_status != ShiftReportGenerationStatus.READY or not report.storage_key:
            raise StateTransitionError("Report is not ready for download.")
        return await self._document_storage.get_download_url(storage_key=report.storage_key)


@dataclass(frozen=True, slots=True, kw_only=True)
class GetAdminDocumentDownloadUrlQuery:
    document_id: UUID


class GetAdminDocumentDownloadUrlHandler:
    def __init__(
        self,
        *,
        documents: DocumentRepository,
        document_storage: DocumentStoragePort,
    ) -> None:
        self._documents = documents
        self._document_storage = document_storage

    async def __call__(self, query: GetAdminDocumentDownloadUrlQuery) -> str:
        document = await self._require_document(query.document_id)
        return await self._document_storage.get_download_url(storage_key=document.storage_key)

    async def _require_document(self, document_id: UUID) -> Document:
        document = await self._documents.get_by_id(document_id)
        if document is None:
            raise EntityNotFoundError("Document is not found.")
        return document
