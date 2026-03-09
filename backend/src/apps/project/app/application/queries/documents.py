from dataclasses import dataclass
from uuid import UUID

from app.application.ports.domain import (
    DocumentRepository,
    DocumentStoragePort,
    ProjectMemberRepository,
    ShiftRepository,
)
from app.application.support import get_actor_member, require_document, require_shift


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
