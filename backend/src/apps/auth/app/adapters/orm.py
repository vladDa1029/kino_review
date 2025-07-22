from sqlalchemy import Table, MetaData, Column, String, Boolean
from sqlalchemy.orm import mapper
from sqlalchemy.dialects.postgresql import UUID

from app.domain import entities


metadata = MetaData()

users = Table(
    "users",
    metadata,
    Column("oid", UUID(as_uuid=True), primary_key=True),
    Column("email", String(255), unique=True),
    Column("password", String(255)),
    Column("is_active", Boolean, default=False),
    Column("is_superuser", Boolean, default=False),
    Column("is_verified", Boolean, default=False),
)


def start_mappers():
    mapper(entities.User, users)
