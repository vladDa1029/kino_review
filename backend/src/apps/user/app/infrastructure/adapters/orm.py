from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    MetaData,
    String,
    Table,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import composite, registry, relationship

from app.domain.entity.base import (
    Camera,
    CameraTripod,
    Description,
    Image,
    Light,
    LightTripod,
    Microfon,
    Requisite,
    Sound,
    Spare_time,
    User,
)
from app.domain.value.email import Email
from app.domain.value.phone import Phone
from app.domain.value.status import AvailabilityStatus

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)
mapper_registry = registry(metadata=metadata)

users = Table(
    "users",
    metadata,
    Column("oid", UUID(as_uuid=True), primary_key=True),
    Column("email", String(255), unique=True, nullable=False),
    Column("is_active", Boolean, nullable=False),
    Column("is_superuser", Boolean, nullable=False),
    Column("is_verified", Boolean, nullable=False),
    Column("create_at", DateTime(timezone=True), default=datetime.now, nullable=False),
)

descriptions = Table(
    "descriptions",
    metadata,
    Column("oid", UUID(as_uuid=True), primary_key=True),
    Column(
        "user_id",
        UUID(as_uuid=True),
        ForeignKey("users.oid"),
        unique=True,
        nullable=False,
    ),
    Column("username", String(255), nullable=False),
    Column("phone", String(32), nullable=False),
)

free_users_timing = Table(
    "free_users_timing",
    metadata,
    Column("oid", UUID(as_uuid=True), primary_key=True),
    Column(
        "user_id",
        UUID(as_uuid=True),
        ForeignKey("users.oid"),
        nullable=False,
    ),
    Column("start_time", DateTime(timezone=True), nullable=False),
    Column("end_time", DateTime(timezone=True), nullable=False),
    Column("status", String(32), nullable=False),
)

microfon_free_times = Table(
    "microfon_free_times",
    metadata,
    Column("oid", UUID(as_uuid=True), primary_key=True),
    Column(
        "microfon_id",
        UUID(as_uuid=True),
        ForeignKey("microfons.oid"),
        nullable=False,
    ),
    Column("start_time", DateTime(timezone=True), nullable=False),
    Column("end_time", DateTime(timezone=True), nullable=False),
    Column("status", String(32), nullable=False),
)

camera_free_times = Table(
    "camera_free_times",
    metadata,
    Column("oid", UUID(as_uuid=True), primary_key=True),
    Column(
        "camera_id",
        UUID(as_uuid=True),
        ForeignKey("cameras.oid"),
        nullable=False,
    ),
    Column("start_time", DateTime(timezone=True), nullable=False),
    Column("end_time", DateTime(timezone=True), nullable=False),
    Column("status", String(32), nullable=False),
)

camera_tripod_free_times = Table(
    "camera_tripod_free_times",
    metadata,
    Column("oid", UUID(as_uuid=True), primary_key=True),
    Column(
        "camera_tripod_id",
        UUID(as_uuid=True),
        ForeignKey("camera_tripods.oid"),
        nullable=False,
    ),
    Column("start_time", DateTime(timezone=True), nullable=False),
    Column("end_time", DateTime(timezone=True), nullable=False),
    Column("status", String(32), nullable=False),
)

light_free_times = Table(
    "light_free_times",
    metadata,
    Column("oid", UUID(as_uuid=True), primary_key=True),
    Column(
        "light_id",
        UUID(as_uuid=True),
        ForeignKey("lights.oid"),
        nullable=False,
    ),
    Column("start_time", DateTime(timezone=True), nullable=False),
    Column("end_time", DateTime(timezone=True), nullable=False),
    Column("status", String(32), nullable=False),
)

light_tripod_free_times = Table(
    "light_tripod_free_times",
    metadata,
    Column("oid", UUID(as_uuid=True), primary_key=True),
    Column(
        "light_tripod_id",
        UUID(as_uuid=True),
        ForeignKey("light_tripods.oid"),
        nullable=False,
    ),
    Column("start_time", DateTime(timezone=True), nullable=False),
    Column("end_time", DateTime(timezone=True), nullable=False),
    Column("status", String(32), nullable=False),
)

sound_free_times = Table(
    "sound_free_times",
    metadata,
    Column("oid", UUID(as_uuid=True), primary_key=True),
    Column(
        "sound_id",
        UUID(as_uuid=True),
        ForeignKey("sounds.oid"),
        nullable=False,
    ),
    Column("start_time", DateTime(timezone=True), nullable=False),
    Column("end_time", DateTime(timezone=True), nullable=False),
    Column("status", String(32), nullable=False),
)

requisite_free_times = Table(
    "requisite_free_times",
    metadata,
    Column("oid", UUID(as_uuid=True), primary_key=True),
    Column(
        "requisite_id",
        UUID(as_uuid=True),
        ForeignKey("requisites.oid"),
        nullable=False,
    ),
    Column("start_time", DateTime(timezone=True), nullable=False),
    Column("end_time", DateTime(timezone=True), nullable=False),
    Column("status", String(32), nullable=False),
)

microfons = Table(
    "microfons",
    metadata,
    Column("oid", UUID(as_uuid=True), primary_key=True),
    Column("users_id", UUID(as_uuid=True), ForeignKey("users.oid"), nullable=False),
    Column("title", String(255), nullable=False),
    Column("description", String(255), nullable=False),
    Column("type", String(64), nullable=False),
    Column("create_at", DateTime(timezone=True), default=datetime.now, nullable=False),
)

cameras = Table(
    "cameras",
    metadata,
    Column("oid", UUID(as_uuid=True), primary_key=True),
    Column("users_id", UUID(as_uuid=True), ForeignKey("users.oid"), nullable=False),
    Column("title", String(255), nullable=False),
    Column("description", String(255), nullable=False),
    Column("type", String(64), nullable=False),
    Column("create_at", DateTime(timezone=True), default=datetime.now, nullable=False),
)

camera_tripods = Table(
    "camera_tripods",
    metadata,
    Column("oid", UUID(as_uuid=True), primary_key=True),
    Column("users_id", UUID(as_uuid=True), ForeignKey("users.oid"), nullable=False),
    Column("title", String(255), nullable=False),
    Column("description", String(255), nullable=False),
    Column("type", String(64), nullable=False),
    Column("create_at", DateTime(timezone=True), default=datetime.now, nullable=False),
)

lights = Table(
    "lights",
    metadata,
    Column("oid", UUID(as_uuid=True), primary_key=True),
    Column("users_id", UUID(as_uuid=True), ForeignKey("users.oid"), nullable=False),
    Column("title", String(255), nullable=False),
    Column("description", String(255), nullable=False),
    Column("type", String(64), nullable=False),
    Column("create_at", DateTime(timezone=True), default=datetime.now, nullable=False),
)

light_tripods = Table(
    "light_tripods",
    metadata,
    Column("oid", UUID(as_uuid=True), primary_key=True),
    Column("users_id", UUID(as_uuid=True), ForeignKey("users.oid"), nullable=False),
    Column("title", String(255), nullable=False),
    Column("description", String(255), nullable=False),
    Column("type", String(64), nullable=False),
    Column("create_at", DateTime(timezone=True), default=datetime.now, nullable=False),
)

sounds = Table(
    "sounds",
    metadata,
    Column("oid", UUID(as_uuid=True), primary_key=True),
    Column("users_id", UUID(as_uuid=True), ForeignKey("users.oid"), nullable=False),
    Column("title", String(255), nullable=False),
    Column("description", String(255), nullable=False),
    Column("type", String(64), nullable=False),
    Column("create_at", DateTime(timezone=True), default=datetime.now, nullable=False),
)

requisites = Table(
    "requisites",
    metadata,
    Column("oid", UUID(as_uuid=True), primary_key=True),
    Column("users_id", UUID(as_uuid=True), ForeignKey("users.oid"), nullable=False),
    Column("title", String(255), nullable=False),
    Column("description", String(255), nullable=False),
    Column("type", String(64), nullable=False),
    Column("size", String(64), nullable=False),
    Column("create_at", DateTime(timezone=True), default=datetime.now, nullable=False),
)

images = Table(
    "images",
    metadata,
    Column("oid", UUID(as_uuid=True), primary_key=True),
    Column(
        "requisite_id",
        UUID(as_uuid=True),
        ForeignKey("requisites.oid"),
        nullable=False,
    ),
    Column("file", String(255), nullable=False),
    Column("title", String(255), nullable=False),
    Column("storage_key", String(255), nullable=False),
    Column("bucket", String(255), nullable=False),
    Column("mime_type", String(128), nullable=False),
    Column("size", BigInteger, nullable=False),
    Column("description", String(255), nullable=False),
    Column("create_at", DateTime(timezone=True), default=datetime.now, nullable=False),
)


def start_mappers() -> None:
    mapper_registry.map_imperatively(
        User,
        users,
        properties={
            "oid": users.c.oid,
            "email": composite(Email, users.c.email),
            "is_active": users.c.is_active,
            "is_superuser": users.c.is_superuser,
            "is_verified": users.c.is_verified,
            "create_at": users.c.create_at,
            "description": relationship(
                "Description",
                back_populates="user",
                uselist=False,
            ),
            "microfons": relationship("Microfon", back_populates="user"),
            "cameras": relationship("Camera", back_populates="user"),
            "camera_tripods": relationship("CameraTripod", back_populates="user"),
            "lights": relationship("Light", back_populates="user"),
            "light_tripods": relationship("LightTripod", back_populates="user"),
            "sounds": relationship("Sound", back_populates="user"),
            "requisites": relationship("Requisite", back_populates="user"),
        },
        column_prefix="_",
    )
    mapper_registry.map_imperatively(
        Description,
        descriptions,
        properties={
            "oid": descriptions.c.oid,
            "user_id": descriptions.c.user_id,
            "username": descriptions.c.username,
            "phone": composite(Phone, descriptions.c.phone),
            "user": relationship("User", back_populates="description"),
        },
        column_prefix="_",
    )
    mapper_registry.map_imperatively(
        Spare_time,
        free_users_timing,
        properties={
            "oid": free_users_timing.c.oid,
            "obj": free_users_timing.c.user_id,
            "start_time": free_users_timing.c.start_time,
            "end_time": free_users_timing.c.end_time,
            "status": composite(AvailabilityStatus, free_users_timing.c.status),
        },
        column_prefix="_",
    )
    mapper_registry.map_imperatively(
        Microfon,
        microfons,
        properties={
            "oid": microfons.c.oid,
            "users_id": microfons.c.users_id,
            "title": microfons.c.title,
            "description": microfons.c.description,
            "type": microfons.c.type,
            "create_at": microfons.c.create_at,
            "user": relationship("User", back_populates="microfons"),
        },
        column_prefix="_",
    )
    mapper_registry.map_imperatively(
        Camera,
        cameras,
        properties={
            "oid": cameras.c.oid,
            "users_id": cameras.c.users_id,
            "title": cameras.c.title,
            "description": cameras.c.description,
            "type": cameras.c.type,
            "create_at": cameras.c.create_at,
            "user": relationship("User", back_populates="cameras"),
        },
        column_prefix="_",
    )
    mapper_registry.map_imperatively(
        CameraTripod,
        camera_tripods,
        properties={
            "oid": camera_tripods.c.oid,
            "users_id": camera_tripods.c.users_id,
            "title": camera_tripods.c.title,
            "description": camera_tripods.c.description,
            "type": camera_tripods.c.type,
            "create_at": camera_tripods.c.create_at,
            "user": relationship("User", back_populates="camera_tripods"),
        },
        column_prefix="_",
    )
    mapper_registry.map_imperatively(
        Light,
        lights,
        properties={
            "oid": lights.c.oid,
            "users_id": lights.c.users_id,
            "title": lights.c.title,
            "description": lights.c.description,
            "type": lights.c.type,
            "create_at": lights.c.create_at,
            "user": relationship("User", back_populates="lights"),
        },
        column_prefix="_",
    )
    mapper_registry.map_imperatively(
        LightTripod,
        light_tripods,
        properties={
            "oid": light_tripods.c.oid,
            "users_id": light_tripods.c.users_id,
            "title": light_tripods.c.title,
            "description": light_tripods.c.description,
            "type": light_tripods.c.type,
            "create_at": light_tripods.c.create_at,
            "user": relationship("User", back_populates="light_tripods"),
        },
        column_prefix="_",
    )
    mapper_registry.map_imperatively(
        Sound,
        sounds,
        properties={
            "oid": sounds.c.oid,
            "users_id": sounds.c.users_id,
            "title": sounds.c.title,
            "description": sounds.c.description,
            "type": sounds.c.type,
            "create_at": sounds.c.create_at,
            "user": relationship("User", back_populates="sounds"),
        },
        column_prefix="_",
    )
    mapper_registry.map_imperatively(
        Requisite,
        requisites,
        properties={
            "oid": requisites.c.oid,
            "users_id": requisites.c.users_id,
            "title": requisites.c.title,
            "description": requisites.c.description,
            "type": requisites.c.type,
            "size": requisites.c.size,
            "create_at": requisites.c.create_at,
            "user": relationship("User", back_populates="requisites"),
            "images": relationship("Image", back_populates="requisite"),
        },
        column_prefix="_",
    )
    mapper_registry.map_imperatively(
        Image,
        images,
        properties={
            "oid": images.c.oid,
            "requisite_id": images.c.requisite_id,
            "file": images.c.file,
            "title": images.c.title,
            "storage_key": images.c.storage_key,
            "bucket": images.c.bucket,
            "mime_type": images.c.mime_type,
            "size": images.c.size,
            "description": images.c.description,
            "create_at": images.c.create_at,
            "requisite": relationship("Requisite", back_populates="images"),
        },
        column_prefix="_",
    )
