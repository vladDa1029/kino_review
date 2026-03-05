from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from app.domain.entities import Document, ProjectMember, Shift
from app.domain.enums import DocumentStatus, DocumentType
from app.domain.errors.business import StateTransitionError
from app.domain.policy.member_access import DirectorMemberPolicy


@dataclass
class DocumentService:
    director_policy: DirectorMemberPolicy = field(default_factory=DirectorMemberPolicy)

    def upload(
        self,
        *,
        actor: ProjectMember,
        shift: Shift,
        document_id: UUID,
        doc_type: DocumentType,
        filename: str,
        title: str,
        storage_key: str,
        bucket: str,
        mime_type: str,
        size: int,
        description: str | None,
        now: datetime,
    ) -> Document:
        self.director_policy.check(actor, action="manage documents")
        if size <= 0:
            raise StateTransitionError("Document size must be greater than zero.")
        return Document(
            shift_id=shift.oid,
            doc_type=doc_type,
            filename=filename,
            title=title,
            storage_key=storage_key,
            bucket=bucket,
            mime_type=mime_type,
            size=size,
            owner_id=actor.user_id,
            description=description,
            version=1,
            status=DocumentStatus.ACTIVE,
            oid=document_id,
            created_at=now,
        )

    def delete(self, *, actor: ProjectMember, document: Document) -> None:
        self.director_policy.check(actor, action="manage documents")
        if document.status == DocumentStatus.DELETED:
            raise StateTransitionError("Document is already deleted.")
        document.status = DocumentStatus.DELETED
