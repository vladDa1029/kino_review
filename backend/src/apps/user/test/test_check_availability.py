import asyncio
from datetime import datetime
from uuid import uuid4

import pytest

from app.application.commands.check_availability import (
    CheckAvailabilityCommand,
    CheckAvailabilityHandler,
)
from app.domain.entity.base import BaseId, Spare_time
from app.domain.errors.availability import AvailabilityNotFoundError
from app.domain.service.availability_service import AvailabilityService
from app.domain.value.status import AvailabilityStatus
from test.helpers import FakeEntityRepository, FakeSpareTimeRepository, make_user


def test_check_availability_handler_validates_without_mutation() -> None:
    user_id = BaseId(uuid4())
    obj_id = BaseId(uuid4())
    free_window = Spare_time(
        oid=BaseId(uuid4()),
        obj=obj_id,
        start_time=datetime(2024, 1, 1, 10, 0, 0),
        end_time=datetime(2024, 1, 1, 14, 0, 0),
        status=AvailabilityStatus("free"),
    )
    spare_time_repo = FakeSpareTimeRepository([free_window])
    handler = CheckAvailabilityHandler(
        user_repository=FakeEntityRepository([make_user(user_id, is_active=True)]),
        spare_time_repository=spare_time_repo,
        microfon_free_time_repository=FakeSpareTimeRepository(),
        camera_free_time_repository=FakeSpareTimeRepository(),
        camera_tripod_free_time_repository=FakeSpareTimeRepository(),
        light_free_time_repository=FakeSpareTimeRepository(),
        light_tripod_free_time_repository=FakeSpareTimeRepository(),
        sound_free_time_repository=FakeSpareTimeRepository(),
        requisite_free_time_repository=FakeSpareTimeRepository(),
        service=AvailabilityService(),
    )

    asyncio.run(
        handler(
            CheckAvailabilityCommand(
                user_id=user_id,
                owner_id=user_id,
                obj_id=obj_id,
                start_time=datetime(2024, 1, 1, 11, 0, 0),
                end_time=datetime(2024, 1, 1, 12, 0, 0),
            )
        )
    )

    assert spare_time_repo.added == []
    assert spare_time_repo.updated == []
    assert spare_time_repo.deleted == []


def test_check_availability_handler_raises_when_no_window_available() -> None:
    user_id = BaseId(uuid4())
    obj_id = BaseId(uuid4())
    spare_time_repo = FakeSpareTimeRepository()
    handler = CheckAvailabilityHandler(
        user_repository=FakeEntityRepository([make_user(user_id, is_active=True)]),
        spare_time_repository=spare_time_repo,
        microfon_free_time_repository=FakeSpareTimeRepository(),
        camera_free_time_repository=FakeSpareTimeRepository(),
        camera_tripod_free_time_repository=FakeSpareTimeRepository(),
        light_free_time_repository=FakeSpareTimeRepository(),
        light_tripod_free_time_repository=FakeSpareTimeRepository(),
        sound_free_time_repository=FakeSpareTimeRepository(),
        requisite_free_time_repository=FakeSpareTimeRepository(),
        service=AvailabilityService(),
    )

    with pytest.raises(AvailabilityNotFoundError):
        asyncio.run(
            handler(
                CheckAvailabilityCommand(
                    user_id=user_id,
                    owner_id=user_id,
                    obj_id=obj_id,
                    start_time=datetime(2024, 1, 1, 11, 0, 0),
                    end_time=datetime(2024, 1, 1, 12, 0, 0),
                )
            )
        )
