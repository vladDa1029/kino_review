import asyncio
from datetime import datetime
from uuid import uuid4

import pytest

from app.application.commands.check_availability import (
    CheckAvailabilityCommand,
    CheckAvailabilityHandler,
)
from app.application.resource_ownership import ResourceOwnershipResolver
from app.domain.entity.base import BaseId, Camera, Spare_time
from app.domain.errors.availability import AvailabilityNotFoundError
from app.domain.errors.policy import OwnershipError
from app.domain.policy.ownership import OwnershipPolicy
from app.domain.service.availability_service import AvailabilityService
from app.domain.value.status import AvailabilityStatus
from test.helpers import FakeEntityRepository, FakeSpareTimeRepository, make_user


def make_resource_ownership_resolver(**repositories) -> ResourceOwnershipResolver:
    empty = FakeEntityRepository()
    return ResourceOwnershipResolver(
        microfon_repository=repositories.get("microfon_repository", empty),
        camera_repository=repositories.get("camera_repository", empty),
        camera_tripod_repository=repositories.get("camera_tripod_repository", empty),
        light_repository=repositories.get("light_repository", empty),
        light_tripod_repository=repositories.get("light_tripod_repository", empty),
        sound_repository=repositories.get("sound_repository", empty),
        requisite_repository=repositories.get("requisite_repository", empty),
        ownership_policy=OwnershipPolicy(),
    )


def test_check_availability_handler_validates_without_mutation() -> None:
    user_id = BaseId(uuid4())
    obj_id = user_id
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
        resource_ownership=make_resource_ownership_resolver(),
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
    obj_id = user_id
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
        resource_ownership=make_resource_ownership_resolver(),
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


def test_check_availability_handler_rejects_resource_owned_by_another_user() -> None:
    user_id = BaseId(uuid4())
    other_user_id = BaseId(uuid4())
    resource_id = BaseId(uuid4())
    camera = Camera(
        oid=resource_id,
        users_id=other_user_id,
        title="Sony",
        description="Camera",
        type="mirrorless",
        create_at=datetime(2024, 1, 1, 9, 0, 0),
    )
    free_window = Spare_time(
        oid=BaseId(uuid4()),
        obj=resource_id,
        start_time=datetime(2024, 1, 1, 10, 0, 0),
        end_time=datetime(2024, 1, 1, 14, 0, 0),
        status=AvailabilityStatus("free"),
    )
    handler = CheckAvailabilityHandler(
        user_repository=FakeEntityRepository([make_user(user_id, is_active=True)]),
        spare_time_repository=FakeSpareTimeRepository(),
        microfon_free_time_repository=FakeSpareTimeRepository(),
        camera_free_time_repository=FakeSpareTimeRepository([free_window]),
        camera_tripod_free_time_repository=FakeSpareTimeRepository(),
        light_free_time_repository=FakeSpareTimeRepository(),
        light_tripod_free_time_repository=FakeSpareTimeRepository(),
        sound_free_time_repository=FakeSpareTimeRepository(),
        requisite_free_time_repository=FakeSpareTimeRepository(),
        resource_ownership=make_resource_ownership_resolver(
            camera_repository=FakeEntityRepository([camera])
        ),
        service=AvailabilityService(),
    )

    with pytest.raises(OwnershipError):
        asyncio.run(
            handler(
                CheckAvailabilityCommand(
                    user_id=user_id,
                    owner_id=user_id,
                    obj_id=resource_id,
                    start_time=datetime(2024, 1, 1, 11, 0, 0),
                    end_time=datetime(2024, 1, 1, 12, 0, 0),
                )
            )
        )
