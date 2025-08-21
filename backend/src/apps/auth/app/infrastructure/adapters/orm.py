from sqlalchemy import Table, MetaData, Column, String, Boolean, DateTime
from datetime import datetime
from sqlalchemy.orm import registry, synonym
from sqlalchemy.dialects.postgresql import UUID

from app.domain import entities
from app.domain.values import Email


metadata = MetaData()
mapper_registry = registry(metadata=metadata)

users = Table(
    "users",
    metadata,
    Column("username", String(255), unique=True),
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
            "email": synonym(
                "email_str",
                descriptor=property(
                    lambda obj: Email(obj.email_str),
                    lambda obj, value: setattr(obj, "email_str", str(value)),
                ),
            ),
            "email_str": users.c.email,
        },
    )
