from dataclasses import dataclass
from uuid import UUID

from app.application.ports.domain import (
    DocumentRepository,
    DocumentStoragePort,
    ProjectMemberRepository,
    ShiftRepository,
)
from app.application.support import get_actor_member, require_document, require_shift
from app.domain.entities import Document
from app.domain.enums import DocumentStatus, DocumentType
from app.domain.errors.business import EntityNotFoundError


@dataclass(frozen=True, slots=True, kw_only=True)
class GetDocumentDownloadUrlQuery:
    document_id: UUID
    actor_user_id: UUID


class GetDocumentDownloadUrlHandler:
    def __init__(
        self,
        *,
        documents: DocumentRepository,
        shifts: ShiftRepository,
        project_members: ProjectMemberRepository,
        document_storage: DocumentStoragePort,
    ) -> None:
        self._documents = documents
        self._shifts = shifts
        self._project_members = project_members
        self._document_storage = document_storage

    async def __call__(self, query: GetDocumentDownloadUrlQuery) -> str:
        document = await require_document(
            documents=self._documents,
            document_id=query.document_id,
        )
        shift = await require_shift(shifts=self._shifts, shift_id=document.shift_id)
        await get_actor_member(
            project_members=self._project_members,
            project_id=shift.project_id,
            user_id=query.actor_user_id,
        )
        return await self._document_storage.get_download_url(storage_key=document.storage_key)


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


def _require_report(document: Document) -> Document:
    if (
        int(document.doc_type) != int(DocumentType.REPORT)
        or int(document.status) == int(DocumentStatus.DELETED)
    ):
        raise EntityNotFoundError("Report is not found.")
    return document


class ListShiftReportsHandler:
    def __init__(
        self,
        *,
        documents: DocumentRepository,
        shifts: ShiftRepository,
        project_members: ProjectMemberRepository,
    ) -> None:
        self._documents = documents
        self._shifts = shifts
        self._project_members = project_members

    async def __call__(self, query: ListShiftReportsQuery) -> list[Document]:
        shift = await require_shift(shifts=self._shifts, shift_id=query.shift_id)
        await get_actor_member(
            project_members=self._project_members,
            project_id=shift.project_id,
            user_id=query.actor_user_id,
        )
        documents = await self._documents.list_by_shift(query.shift_id)
        return [
            document
            for document in documents
            if int(document.doc_type) == int(DocumentType.REPORT)
            and int(document.status) != int(DocumentStatus.DELETED)
        ]


class GetReportHandler:
    def __init__(
        self,
        *,
        documents: DocumentRepository,
        shifts: ShiftRepository,
        project_members: ProjectMemberRepository,
    ) -> None:
        self._documents = documents
        self._shifts = shifts
        self._project_members = project_members

    async def __call__(self, query: GetReportQuery) -> Document:
        document = _require_report(
            await require_document(
                documents=self._documents,
                document_id=query.report_id,
            )
        )
        shift = await require_shift(shifts=self._shifts, shift_id=document.shift_id)
        await get_actor_member(
            project_members=self._project_members,
            project_id=shift.project_id,
            user_id=query.actor_user_id,
        )
        return document


class GetReportDownloadUrlHandler:
    def __init__(
        self,
        *,
        documents: DocumentRepository,
        shifts: ShiftRepository,
        project_members: ProjectMemberRepository,
        document_storage: DocumentStoragePort,
    ) -> None:
        self._documents = documents
        self._shifts = shifts
        self._project_members = project_members
        self._document_storage = document_storage

    async def __call__(self, query: GetReportDownloadUrlQuery) -> str:
        document = _require_report(
            await require_document(
                documents=self._documents,
                document_id=query.report_id,
            )
        )
        shift = await require_shift(shifts=self._shifts, shift_id=document.shift_id)
        await get_actor_member(
            project_members=self._project_members,
            project_id=shift.project_id,
            user_id=query.actor_user_id,
        )
        return await self._document_storage.get_download_url(storage_key=document.storage_key)
