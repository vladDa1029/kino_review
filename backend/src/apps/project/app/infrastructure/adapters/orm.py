from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, UniqueConstraint, Uuid
from sqlalchemy.orm import composite, registry

from app.domain.entities import (
    Document,
    Project,
    ProjectMember,
    ReservationOutboxMessage,
    Shift,
    ShiftParticipant,
    ShiftResourceRequest,
)
from app.domain.enums import (
    DocumentStatus,
    DocumentType,
    ProjectMemberStatus,
    ProjectRole,
    ProjectStatus,
    ResourceRequestStatus,
    ShiftParticipantStatus,
    ShiftStatus,
)
from app.domain.value_objects import TimeInterval

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)
mapper_registry = registry(metadata=metadata)


projects = Table(
    "projects",
    metadata,
    Column("oid", Uuid(as_uuid=True), primary_key=True),
    Column("title", String(255), nullable=False),
    Column("description", String(2000), nullable=False, default=""),
    Column("owner_id", Uuid(as_uuid=True), nullable=False, index=True),
    Column("status", Integer, nullable=False, default=int(ProjectStatus.ACTIVE)),
    Column("created_at", DateTime(timezone=True), nullable=False, default=datetime.now),
    Column("updated_at", DateTime(timezone=True), nullable=False, default=datetime.now),
)

users_project_role = Table(
    "users_project_role",
    metadata,
    Column("oid", Uuid(as_uuid=True), primary_key=True),
    Column("user_id", Uuid(as_uuid=True), nullable=False, index=True),
    Column("project_id", Uuid(as_uuid=True), nullable=False, index=True),
    Column("role", Integer, nullable=False, default=int(ProjectRole.DIRECTOR)),
    Column("status", Integer, nullable=False, default=int(ProjectMemberStatus.INVITED)),
    Column("invited_by", Uuid(as_uuid=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, default=datetime.now),
    Column("updated_at", DateTime(timezone=True), nullable=False, default=datetime.now),
    UniqueConstraint("project_id", "user_id"),
)

shift = Table(
    "shift",
    metadata,
    Column("oid", Uuid(as_uuid=True), primary_key=True),
    Column("project_id", Uuid(as_uuid=True), nullable=False, index=True),
    Column("title", String(255), nullable=False),
    Column("description", String(2000), nullable=False, default=""),
    Column("created_at", DateTime(timezone=True), nullable=False, default=datetime.now),
    Column("updated_at", DateTime(timezone=True), nullable=False, default=datetime.now),
    Column("start_time", DateTime(timezone=True), nullable=False),
    Column("end_time", DateTime(timezone=True), nullable=False),
    Column("status", Integer, nullable=False, index=True, default=int(ShiftStatus.DRAFT)),
    Column("created_by", Uuid(as_uuid=True), nullable=False),
    Column("approved_by", Uuid(as_uuid=True), nullable=True),
    Column("approved_at", DateTime(timezone=True), nullable=True),
)

shift_participants = Table(
    "shift_participants",
    metadata,
    Column("oid", Uuid(as_uuid=True), primary_key=True),
    Column("shift_id", Uuid(as_uuid=True), nullable=False, index=True),
    Column("user_id", Uuid(as_uuid=True), nullable=False, index=True),
    Column("role", Integer, nullable=False),
    Column("time_from", DateTime(timezone=True), nullable=False),
    Column("time_to", DateTime(timezone=True), nullable=False),
    Column(
        "status",
        Integer,
        nullable=False,
        index=True,
        default=int(ShiftParticipantStatus.INVITED),
    ),
    Column("user_reservation_id", Uuid(as_uuid=True), nullable=True),
    Column("added_by", Uuid(as_uuid=True), nullable=False),
    Column("reserve_failure_reason", String(2000), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, default=datetime.now),
    Column("updated_at", DateTime(timezone=True), nullable=False, default=datetime.now),
    UniqueConstraint("shift_id", "user_id"),
)

documents = Table(
    "documents",
    metadata,
    Column("oid", Uuid(as_uuid=True), primary_key=True),
    Column("shift_id", Uuid(as_uuid=True), nullable=False, index=True),
    Column("doc_type", Integer, nullable=False, default=int(DocumentType.PLAN)),
    Column("filename", String(512), nullable=False),
    Column("title", String(512), nullable=False),
    Column("storage_key", String(1024), nullable=False, unique=True),
    Column("bucket", String(255), nullable=False),
    Column("mime_type", String(255), nullable=False),
    Column("size", Integer, nullable=False),
    Column("owner_id", Uuid(as_uuid=True), nullable=False),
    Column("description", String(2000), nullable=True),
    Column("version", Integer, nullable=False, default=1),
    Column("status", Integer, nullable=False, default=int(DocumentStatus.ACTIVE)),
    Column("created_at", DateTime(timezone=True), nullable=False, default=datetime.now),
)

shift_resource_requests = Table(
    "shift_resource_requests",
    metadata,
    Column("oid", Uuid(as_uuid=True), primary_key=True),
    Column("project_id", Uuid(as_uuid=True), nullable=False, index=True),
    Column("shift_id", Uuid(as_uuid=True), nullable=False, index=True),
    Column("resource_type", String(64), nullable=False),
    Column("resource_id", Uuid(as_uuid=True), nullable=False),
    Column("resource_owner_user_id", Uuid(as_uuid=True), nullable=False, index=True),
    Column("requested_by_user_id", Uuid(as_uuid=True), nullable=False),
    Column("time_from", DateTime(timezone=True), nullable=False),
    Column("time_to", DateTime(timezone=True), nullable=False),
    Column(
        "status",
        Integer,
        nullable=False,
        index=True,
        default=int(ResourceRequestStatus.PENDING_OWNER),
    ),
    Column("resource_reservation_id", Uuid(as_uuid=True), nullable=True),
    Column("rejection_reason", String(2000), nullable=True),
    Column("reserve_failure_reason", String(2000), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, default=datetime.now),
    Column("updated_at", DateTime(timezone=True), nullable=False, default=datetime.now),
)

reservation_outbox = Table(
    "reservation_outbox",
    metadata,
    Column("oid", Uuid(as_uuid=True), primary_key=True),
    Column("operation", String(64), nullable=False),
    Column("aggregate_id", Uuid(as_uuid=True), nullable=False, index=True),
    Column("status", String(32), nullable=False, index=True),
    Column("attempts", Integer, nullable=False, default=0),
    Column("last_error", String(2000), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, default=datetime.now),
    Column("updated_at", DateTime(timezone=True), nullable=False, default=datetime.now),
)


def start_mappers() -> None:
    mapper_registry.map_imperatively(
        Project,
        projects,
        properties={
            "oid": projects.c.oid,
            "title": projects.c.title,
            "description": projects.c.description,
            "owner_id": projects.c.owner_id,
            "status": projects.c.status,
            "created_at": projects.c.created_at,
            "updated_at": projects.c.updated_at,
        },
        column_prefix="_",
    )
    mapper_registry.map_imperatively(
        ProjectMember,
        users_project_role,
        properties={
            "oid": users_project_role.c.oid,
            "user_id": users_project_role.c.user_id,
            "project_id": users_project_role.c.project_id,
            "role": users_project_role.c.role,
            "status": users_project_role.c.status,
            "invited_by": users_project_role.c.invited_by,
            "created_at": users_project_role.c.created_at,
            "updated_at": users_project_role.c.updated_at,
        },
        column_prefix="_",
    )
    mapper_registry.map_imperatively(
        Shift,
        shift,
        properties={
            "oid": shift.c.oid,
            "project_id": shift.c.project_id,
            "title": shift.c.title,
            "description": shift.c.description,
            "start_time": shift.c.start_time,
            "end_time": shift.c.end_time,
            "created_by": shift.c.created_by,
            "status": shift.c.status,
            "approved_by": shift.c.approved_by,
            "approved_at": shift.c.approved_at,
            "created_at": shift.c.created_at,
            "updated_at": shift.c.updated_at,
            "interval": composite(TimeInterval, "start_time", "end_time"),
        },
        column_prefix="_",
    )
    mapper_registry.map_imperatively(
        ShiftParticipant,
        shift_participants,
        properties={
            "oid": shift_participants.c.oid,
            "shift_id": shift_participants.c.shift_id,
            "user_id": shift_participants.c.user_id,
            "role": shift_participants.c.role,
            "time_from": shift_participants.c.time_from,
            "time_to": shift_participants.c.time_to,
            "status": shift_participants.c.status,
            "added_by": shift_participants.c.added_by,
            "user_reservation_id": shift_participants.c.user_reservation_id,
            "reserve_failure_reason": shift_participants.c.reserve_failure_reason,
            "created_at": shift_participants.c.created_at,
            "updated_at": shift_participants.c.updated_at,
            "interval": composite(TimeInterval, "time_from", "time_to"),
        },
        column_prefix="_",
    )
    mapper_registry.map_imperatively(
        Document,
        documents,
        properties={
            "oid": documents.c.oid,
            "shift_id": documents.c.shift_id,
            "doc_type": documents.c.doc_type,
            "filename": documents.c.filename,
            "title": documents.c.title,
            "storage_key": documents.c.storage_key,
            "bucket": documents.c.bucket,
            "mime_type": documents.c.mime_type,
            "size": documents.c.size,
            "owner_id": documents.c.owner_id,
            "description": documents.c.description,
            "version": documents.c.version,
            "status": documents.c.status,
            "created_at": documents.c.created_at,
        },
        column_prefix="_",
    )
    mapper_registry.map_imperatively(
        ShiftResourceRequest,
        shift_resource_requests,
        properties={
            "oid": shift_resource_requests.c.oid,
            "project_id": shift_resource_requests.c.project_id,
            "shift_id": shift_resource_requests.c.shift_id,
            "resource_type": shift_resource_requests.c.resource_type,
            "resource_id": shift_resource_requests.c.resource_id,
            "resource_owner_user_id": shift_resource_requests.c.resource_owner_user_id,
            "requested_by_user_id": shift_resource_requests.c.requested_by_user_id,
            "time_from": shift_resource_requests.c.time_from,
            "time_to": shift_resource_requests.c.time_to,
            "status": shift_resource_requests.c.status,
            "resource_reservation_id": shift_resource_requests.c.resource_reservation_id,
            "rejection_reason": shift_resource_requests.c.rejection_reason,
            "reserve_failure_reason": shift_resource_requests.c.reserve_failure_reason,
            "created_at": shift_resource_requests.c.created_at,
            "updated_at": shift_resource_requests.c.updated_at,
            "interval": composite(TimeInterval, "time_from", "time_to"),
        },
        column_prefix="_",
    )
    mapper_registry.map_imperatively(
        ReservationOutboxMessage,
        reservation_outbox,
        properties={
            "oid": reservation_outbox.c.oid,
            "operation": reservation_outbox.c.operation,
            "aggregate_id": reservation_outbox.c.aggregate_id,
            "status": reservation_outbox.c.status,
            "attempts": reservation_outbox.c.attempts,
            "last_error": reservation_outbox.c.last_error,
            "created_at": reservation_outbox.c.created_at,
            "updated_at": reservation_outbox.c.updated_at,
        },
        column_prefix="_",
    )
