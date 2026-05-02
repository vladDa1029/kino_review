import asyncio
from datetime import datetime
from uuid import uuid4

import pytest

from app.application.commands.update_equipment import (
    UpdateCameraCommand,
    UpdateCameraHandler,
    UpdateCameraTripodCommand,
    UpdateCameraTripodHandler,
    UpdateLightCommand,
    UpdateLightHandler,
    UpdateLightTripodCommand,
    UpdateLightTripodHandler,
    UpdateMicrofonCommand,
    UpdateMicrofonHandler,
    UpdateRequisiteCommand,
    UpdateRequisiteHandler,
    UpdateSoundCommand,
    UpdateSoundHandler,
)
from app.domain.entity.base import (
    BaseId,
    Camera,
    CameraTripod,
    Light,
    LightTripod,
    Microfon,
    Requisite,
    Sound,
)
from app.domain.service.equipment_service import EquipmentService
from test.helpers import (
    FakeEntityRepository,
    FakeSpareTimeRepository,
    FakeTransaction,
    make_user,
)

UPDATE_CASES = [
    (
        UpdateMicrofonHandler,
        UpdateMicrofonCommand,
        "microfon_repository",
        "microfon_free_time_repository",
        "microfon_id",
        Microfon,
        {"title": "mic", "description": "desc", "type": "shotgun"},
    ),
    (
        UpdateCameraHandler,
        UpdateCameraCommand,
        "camera_repository",
        "camera_free_time_repository",
        "camera_id",
        Camera,
        {"title": "cam", "description": "desc", "type": "dslr"},
    ),
    (
        UpdateCameraTripodHandler,
        UpdateCameraTripodCommand,
        "camera_tripod_repository",
        "camera_tripod_free_time_repository",
        "camera_tripod_id",
        CameraTripod,
        {"title": "tripod", "description": "desc", "type": "fluid"},
    ),
    (
        UpdateLightHandler,
        UpdateLightCommand,
        "light_repository",
        "light_free_time_repository",
        "light_id",
        Light,
        {"title": "light", "description": "desc", "type": "led"},
    ),
    (
        UpdateLightTripodHandler,
        UpdateLightTripodCommand,
        "light_tripod_repository",
        "light_tripod_free_time_repository",
        "light_tripod_id",
        LightTripod,
        {"title": "stand", "description": "desc", "type": "c-stand"},
    ),
    (
        UpdateSoundHandler,
        UpdateSoundCommand,
        "sound_repository",
        "sound_free_time_repository",
        "sound_id",
        Sound,
        {"title": "recorder", "description": "desc", "type": "field"},
    ),
    (
        UpdateRequisiteHandler,
        UpdateRequisiteCommand,
        "requisite_repository",
        "requisite_free_time_repository",
        "requisite_id",
        Requisite,
        {"title": "prop", "description": "desc", "type": "decor", "size": "m"},
    ),
]


@pytest.mark.parametrize(
    (
        "handler_cls",
        "command_cls",
        "repo_param",
        "free_time_repo_param",
        "id_field",
        "entity_cls",
        "payload",
    ),
    UPDATE_CASES,
)
def test_update_equipment_handlers(
    handler_cls,
    command_cls,
    repo_param,
    free_time_repo_param,
    id_field,
    entity_cls,
    payload,
) -> None:
    user_id = BaseId(uuid4())
    user = make_user(user_id, is_active=True)
    entity_id = BaseId(uuid4())

    equipment = entity_cls(
        oid=entity_id,
        users_id=user_id,
        title="old",
        description="old",
        type="old",
        create_at=datetime(2024, 1, 1, 10, 0, 0),
        **({"size": "s"} if entity_cls is Requisite else {}),
    )

    user_repo = FakeEntityRepository([user])
    equipment_repo = FakeEntityRepository([equipment])
    spare_time_repo = FakeSpareTimeRepository([])
    tx = FakeTransaction()

    handler = handler_cls(
        user_repository=user_repo,
        transaction=tx,
        service=EquipmentService(),
        **{repo_param: equipment_repo, free_time_repo_param: spare_time_repo},
    )

    command_kwargs = dict(user_id=user_id, **payload)
    command_kwargs[id_field] = entity_id
    command = command_cls(**command_kwargs)

    asyncio.run(handler(command))

    assert equipment.title == payload["title"]
    assert equipment.description == payload["description"]
    assert equipment.type == payload["type"]
    if isinstance(equipment, Requisite):
        assert equipment.size == payload["size"]
    assert tx.commits == 1
    assert tx.rollbacks == 0
