"""
Negative unit tests for the user service domain layer.

Covers: overlapping spare-time windows (CrossingTimingError),
deleting/updating equipment with reserved windows (ResourceLockedError),
and double description creation (DescriptionAlreadyExistsError).
"""

import asyncio
from datetime import datetime
from uuid import uuid4

import pytest

from app.application.commands.add_spare_time import AddSpareTimeCommand, AddSpareTimeHandler
from app.application.commands.create_description import (
    CreateDescriptionCommand,
    CreateDescriptionHandler,
)
from app.application.commands.delete_equipment import (
    DeleteCameraCommand,
    DeleteCameraHandler,
)
from app.application.commands.update_equipment import (
    UpdateCameraCommand,
    UpdateCameraHandler,
)
from app.domain.entity.base import BaseId, Camera, Description, Spare_time
from app.domain.errors.aggregate import CrossingTimingError
from app.domain.errors.policy import DescriptionAlreadyExistsError, ResourceLockedError
from app.domain.service.description_service import DescriptionService
from app.domain.service.equipment_service import EquipmentService
from app.domain.service.free_time_service import FreeTimeService
from app.domain.value.phone import Phone
from app.domain.value.status import AvailabilityStatus
from test.helpers import (
    FakeDescriptionRepository,
    FakeEntityRepository,
    FakeIdGenerator,
    FakeSpareTimeRepository,
    FakeTransaction,
    make_user,
)

# ---------------------------------------------------------------------------
# CrossingTimingError — overlapping spare-time windows
# ---------------------------------------------------------------------------


def test_add_spare_time_raises_when_overlapping() -> None:
    user_id = BaseId(uuid4())
    user = make_user(user_id, is_active=True)

    existing_timing_id = BaseId(uuid4())
    existing_timing = Spare_time(
        oid=existing_timing_id,
        obj=user_id,
        start_time=datetime(2024, 6, 1, 10, 0, 0),
        end_time=datetime(2024, 6, 1, 14, 0, 0),
    )

    user_repo = FakeEntityRepository([user])
    spare_time_repo = FakeSpareTimeRepository([existing_timing])
    tx = FakeTransaction()
    id_gen = FakeIdGenerator(BaseId(uuid4()))
    handler = AddSpareTimeHandler(
        user_repository=user_repo,
        spare_time_repository=spare_time_repo,
        transaction=tx,
        id_generator=id_gen,
        service=FreeTimeService(),
    )

    # Overlaps with existing [10:00-14:00]
    command = AddSpareTimeCommand(
        user_id=user_id,
        start_time=datetime(2024, 6, 1, 12, 0, 0),
        end_time=datetime(2024, 6, 1, 16, 0, 0),
    )

    with pytest.raises(CrossingTimingError):
        asyncio.run(handler(command))

    assert tx.commits == 0
    assert tx.rollbacks == 1


def test_add_spare_time_raises_when_fully_contained() -> None:
    user_id = BaseId(uuid4())
    user = make_user(user_id, is_active=True)

    existing = Spare_time(
        oid=BaseId(uuid4()),
        obj=user_id,
        start_time=datetime(2024, 6, 1, 8, 0, 0),
        end_time=datetime(2024, 6, 1, 18, 0, 0),
    )

    user_repo = FakeEntityRepository([user])
    spare_time_repo = FakeSpareTimeRepository([existing])
    tx = FakeTransaction()
    handler = AddSpareTimeHandler(
        user_repository=user_repo,
        spare_time_repository=spare_time_repo,
        transaction=tx,
        id_generator=FakeIdGenerator(),
        service=FreeTimeService(),
    )

    # Fully inside existing window — also an overlap
    command = AddSpareTimeCommand(
        user_id=user_id,
        start_time=datetime(2024, 6, 1, 10, 0, 0),
        end_time=datetime(2024, 6, 1, 12, 0, 0),
    )

    with pytest.raises(CrossingTimingError):
        asyncio.run(handler(command))

    assert tx.rollbacks == 1


# ---------------------------------------------------------------------------
# ResourceLockedError — equipment with reserved windows cannot be deleted/updated
# ---------------------------------------------------------------------------


def test_delete_camera_raises_when_window_reserved() -> None:
    user_id = BaseId(uuid4())
    camera_id = BaseId(uuid4())
    user = make_user(user_id, is_active=True)

    camera = Camera(
        oid=camera_id,
        users_id=user_id,
        title="Sony A7",
        description="mirrorless",
        type="cinema",
        create_at=datetime(2024, 1, 1, 0, 0, 0),
    )
    reserved_window = Spare_time(
        oid=BaseId(uuid4()),
        obj=camera_id,
        start_time=datetime(2024, 6, 1, 10, 0, 0),
        end_time=datetime(2024, 6, 1, 14, 0, 0),
        status=AvailabilityStatus("reserved"),
    )

    user_repo = FakeEntityRepository([user])
    camera_repo = FakeEntityRepository([camera])
    spare_time_repo = FakeSpareTimeRepository([reserved_window])
    tx = FakeTransaction()

    handler = DeleteCameraHandler(
        user_repository=user_repo,
        camera_repository=camera_repo,
        camera_free_time_repository=spare_time_repo,
        transaction=tx,
        service=EquipmentService(),
    )

    command = DeleteCameraCommand(user_id=user_id, camera_id=camera_id)

    with pytest.raises(ResourceLockedError):
        asyncio.run(handler(command))

    assert camera_repo.deleted == []
    assert tx.commits == 0
    assert tx.rollbacks == 1


def test_update_camera_raises_when_window_reserved() -> None:
    user_id = BaseId(uuid4())
    camera_id = BaseId(uuid4())
    user = make_user(user_id, is_active=True)

    camera = Camera(
        oid=camera_id,
        users_id=user_id,
        title="Old title",
        description="old desc",
        type="old type",
        create_at=datetime(2024, 1, 1, 0, 0, 0),
    )
    reserved_window = Spare_time(
        oid=BaseId(uuid4()),
        obj=camera_id,
        start_time=datetime(2024, 6, 1, 10, 0, 0),
        end_time=datetime(2024, 6, 1, 14, 0, 0),
        status=AvailabilityStatus("reserved"),
    )

    user_repo = FakeEntityRepository([user])
    camera_repo = FakeEntityRepository([camera])
    spare_time_repo = FakeSpareTimeRepository([reserved_window])
    tx = FakeTransaction()

    handler = UpdateCameraHandler(
        user_repository=user_repo,
        camera_repository=camera_repo,
        camera_free_time_repository=spare_time_repo,
        transaction=tx,
        service=EquipmentService(),
    )

    command = UpdateCameraCommand(
        user_id=user_id,
        camera_id=camera_id,
        title="New title",
        description="new desc",
        type="new type",
    )

    with pytest.raises(ResourceLockedError):
        asyncio.run(handler(command))

    assert camera_repo.updated == []
    assert tx.rollbacks == 1


# ---------------------------------------------------------------------------
# DescriptionAlreadyExistsError — second description for same user is rejected
# ---------------------------------------------------------------------------


def test_create_description_raises_when_already_exists() -> None:
    user_id = BaseId(uuid4())
    user = make_user(user_id, is_active=True)

    existing_desc = Description(
        oid=BaseId(uuid4()),
        user_id=user_id,
        username="existing_user",
        phone=Phone("89001234567"),
    )

    user_repo = FakeEntityRepository([user])
    desc_repo = FakeDescriptionRepository([existing_desc])
    tx = FakeTransaction()
    id_gen = FakeIdGenerator(BaseId(uuid4()))

    handler = CreateDescriptionHandler(
        user_repository=user_repo,
        description_repository=desc_repo,
        transaction=tx,
        id_generator=id_gen,
        service=DescriptionService(),
    )

    command = CreateDescriptionCommand(
        user_id=user_id,
        username="new_user",
        phone="89009876543",
    )

    with pytest.raises(DescriptionAlreadyExistsError):
        asyncio.run(handler(command))

    assert len(desc_repo.added) == 0
    assert tx.commits == 0
    assert tx.rollbacks == 1
