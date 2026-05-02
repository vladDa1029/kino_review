from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, MetaData, String, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import composite, registry

from app.domain import entities
from app.domain.values import Email

metadata = MetaData()
mapper_registry = registry(metadata=metadata)

users = Table(
    "users",
    metadata,
    Column("oid", UUID(as_uuid=True), primary_key=True),
    Column("email", String(255), unique=True, nullable=False),
    Column("password", String(255), nullable=False),
    Column("is_active", Boolean, nullable=False),
    Column("is_superuser", Boolean, nullable=False),
    Column("is_verified", Boolean, nullable=False),
    Column("create_at", DateTime(timezone=True), default=datetime.now),
)


def start_mappers():
    mapper_registry.map_imperatively(
        entities.User,
        users,
        properties={
            "oid": users.c.oid,
            "email": composite(Email, users.c.email),
            "password": users.c.password,
            "is_active": users.c.is_active,
            "is_superuser": users.c.is_superuser,
            "is_verified": users.c.is_verified,
            "create_at": users.c.create_at,
        },
        column_prefix="_",
    )
