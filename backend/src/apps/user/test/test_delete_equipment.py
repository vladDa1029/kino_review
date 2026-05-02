import asyncio
from datetime import datetime
from uuid import uuid4

import pytest

from app.application.commands.delete_equipment import (
    DeleteCameraCommand,
    DeleteCameraHandler,
    DeleteCameraTripodCommand,
    DeleteCameraTripodHandler,
    DeleteLightCommand,
    DeleteLightHandler,
    DeleteLightTripodCommand,
    DeleteLightTripodHandler,
    DeleteMicrofonCommand,
    DeleteMicrofonHandler,
    DeleteRequisiteCommand,
    DeleteRequisiteHandler,
    DeleteSoundCommand,
    DeleteSoundHandler,
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

DELETE_CASES = [
    (
        DeleteMicrofonHandler,
        DeleteMicrofonCommand,
        "microfon_repository",
        "microfon_free_time_repository",
        "microfon_id",
        Microfon,
    ),
    (
        DeleteCameraHandler,
        DeleteCameraCommand,
        "camera_repository",
        "camera_free_time_repository",
        "camera_id",
        Camera,
    ),
    (
        DeleteCameraTripodHandler,
        DeleteCameraTripodCommand,
        "camera_tripod_repository",
        "camera_tripod_free_time_repository",
        "camera_tripod_id",
        CameraTripod,
    ),
    (
        DeleteLightHandler,
        DeleteLightCommand,
        "light_repository",
        "light_free_time_repository",
        "light_id",
        Light,
    ),
    (
        DeleteLightTripodHandler,
        DeleteLightTripodCommand,
        "light_tripod_repository",
        "light_tripod_free_time_repository",
        "light_tripod_id",
        LightTripod,
    ),
    (
        DeleteSoundHandler,
        DeleteSoundCommand,
        "sound_repository",
        "sound_free_time_repository",
        "sound_id",
        Sound,
    ),
    (
        DeleteRequisiteHandler,
        DeleteRequisiteCommand,
        "requisite_repository",
        "requisite_free_time_repository",
        "requisite_id",
        Requisite,
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
    ),
    DELETE_CASES,
)
def test_delete_equipment_handlers(
    handler_cls,
    command_cls,
    repo_param,
    free_time_repo_param,
    id_field,
    entity_cls,
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

    command_kwargs = dict(user_id=user_id)
    command_kwargs[id_field] = entity_id
    command = command_cls(**command_kwargs)

    asyncio.run(handler(command))

    assert equipment_repo.deleted == [equipment]
    assert tx.commits == 1
    assert tx.rollbacks == 0
