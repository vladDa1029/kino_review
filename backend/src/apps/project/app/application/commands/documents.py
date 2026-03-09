from dataclasses import dataclass
from uuid import UUID

from app.application.ports.broker import EventPublisher
from app.application.ports.domain import (
    ClockPort,
    DocumentRepository,
    DocumentStoragePort,
    IdGeneratorPort,
    ProjectMemberRepository,
    ShiftRepository,
)
from app.application.ports.transaction import TransactionManager
from app.application.support import get_actor_member, publish_best_effort, require_shift
from app.domain.entities import Document
from app.domain.enums import DocumentType
from app.domain.services import DocumentService


@dataclass(frozen=True, slots=True, kw_only=True)
class UploadShiftDocumentCommand:
    shift_id: UUID
    actor_user_id: UUID
    doc_type: DocumentType
    title: str
    filename: str
    content: bytes
    content_type: str
    description: str | None = None


class UploadShiftDocumentHandler:
    def __init__(
        self,
        *,
        transaction_manager: TransactionManager,
        clock: ClockPort,
        id_generator: IdGeneratorPort,
        publisher: EventPublisher,
        document_storage: DocumentStoragePort,
        project_members: ProjectMemberRepository,
        shifts: ShiftRepository,
        documents: DocumentRepository,
        document_service: DocumentService,
    ) -> None:
        self._tx = transaction_manager
        self._clock = clock
        self._id_generator = id_generator
        self._publisher = publisher
        self._document_storage = document_storage
        self._project_members = project_members
        self._shifts = shifts
        self._documents = documents
        self._document_service = document_service

    async def __call__(self, command: UploadShiftDocumentCommand) -> Document:
        now = self._clock.now()
        try:
            shift = await require_shift(shifts=self._shifts, shift_id=command.shift_id)
            actor = await get_actor_member(
                project_members=self._project_members,
                project_id=shift.project_id,
                user_id=command.actor_user_id,
            )
            stored = await self._document_storage.upload(
                filename=command.filename,
                content=command.content,
                content_type=command.content_type,
            )
            document = self._document_service.upload(
                actor=actor,
                shift=shift,
                document_id=self._id_generator(),
                doc_type=command.doc_type,
                filename=command.filename,
                title=command.title,
                storage_key=stored.storage_key,
                bucket=stored.bucket,
                mime_type=stored.mime_type,
                size=stored.size,
                description=command.description,
                now=now,
            )
            await self._documents.add(document)
            await self._tx.commit()
        except Exception:
            await self._tx.rollback()
            raise

        await publish_best_effort(
            publisher=self._publisher,
            topic="shift.document_uploaded",
            payload={
                "project_id": str(shift.project_id),
                "shift_id": str(shift.oid),
                "document_id": str(document.oid),
                "doc_type": int(command.doc_type),
            },
        )
        return document
