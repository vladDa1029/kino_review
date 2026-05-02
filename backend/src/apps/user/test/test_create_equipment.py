import asyncio
from datetime import datetime
from uuid import uuid4

import pytest

from app.application.commands.create_equipment import (
    CreateCameraCommand,
    CreateCameraHandler,
    CreateCameraTripodCommand,
    CreateCameraTripodHandler,
    CreateLightCommand,
    CreateLightHandler,
    CreateLightTripodCommand,
    CreateLightTripodHandler,
    CreateRequisiteCommand,
    CreateRequisiteHandler,
    CreateSoundCommand,
    CreateSoundHandler,
)
from app.domain.entity.base import (
    BaseId,
    Camera,
    CameraTripod,
    Light,
    LightTripod,
    Requisite,
    Sound,
)
from app.domain.service.equipment_service import EquipmentService
from test.helpers import (
    FakeEntityRepository,
    FakeIdGenerator,
    FakeTransaction,
    make_user,
)

CREATE_CASES = [
    (
        CreateCameraHandler,
        CreateCameraCommand,
        "camera_repository",
        Camera,
        {"title": "cam", "description": "desc", "type": "dslr"},
    ),
    (
        CreateCameraTripodHandler,
        CreateCameraTripodCommand,
        "camera_tripod_repository",
        CameraTripod,
        {"title": "tripod", "description": "desc", "type": "fluid"},
    ),
    (
        CreateLightHandler,
        CreateLightCommand,
        "light_repository",
        Light,
        {"title": "light", "description": "desc", "type": "led"},
    ),
    (
        CreateLightTripodHandler,
        CreateLightTripodCommand,
        "light_tripod_repository",
        LightTripod,
        {"title": "stand", "description": "desc", "type": "c-stand"},
    ),
    (
        CreateSoundHandler,
        CreateSoundCommand,
        "sound_repository",
        Sound,
        {"title": "recorder", "description": "desc", "type": "field"},
    ),
    (
        CreateRequisiteHandler,
        CreateRequisiteCommand,
        "requisite_repository",
        Requisite,
        {"title": "prop", "description": "desc", "type": "decor", "size": "m"},
    ),
]


@pytest.mark.parametrize(
    ("handler_cls", "command_cls", "repo_param", "entity_cls", "payload"),
    CREATE_CASES,
)
def test_create_equipment_handlers(
    handler_cls, command_cls, repo_param, entity_cls, payload
) -> None:
    user_id = BaseId(uuid4())
    user = make_user(user_id, is_active=True)
    entity_id = BaseId(uuid4())

    user_repo = FakeEntityRepository([user])
    equipment_repo = FakeEntityRepository()
    tx = FakeTransaction()
    id_gen = FakeIdGenerator(entity_id)
    handler = handler_cls(
        user_repository=user_repo,
        transaction=tx,
        id_generator=id_gen,
        service=EquipmentService(),
        **{repo_param: equipment_repo},
    )

    command = command_cls(user_id=user_id, **payload)
    asyncio.run(handler(command))

    assert len(equipment_repo.added) == 1
    created = equipment_repo.added[0]
    assert isinstance(created, entity_cls)
    assert created.oid == entity_id
    assert created.users_id == user_id
    assert created.title == payload["title"]
    assert created.description == payload["description"]
    assert created.type == payload["type"]
    if isinstance(created, Requisite):
        assert created.size == payload["size"]
    assert isinstance(created.create_at, datetime)
    assert tx.commits == 1
    assert tx.rollbacks == 0
