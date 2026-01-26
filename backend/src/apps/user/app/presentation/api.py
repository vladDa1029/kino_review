from uuid import UUID

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter

from app.application.commands.add_image import AddImageCommand, AddImageHandler
from app.application.commands.add_spare_time import (
    AddSpareTimeCommand,
    AddSpareTimeHandler,
)
from app.application.commands.create_description import (
    CreateDescriptionCommand,
    CreateDescriptionHandler,
)
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
from app.application.commands.create_microfon import (
    CreateMicrofonCommand,
    CreateMicrofonHandler,
)
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
from app.application.commands.remove_image import (
    RemoveImageCommand,
    RemoveImageHandler,
)
from app.application.commands.reserve_availability import (
    ReserveAvailabilityCommand,
    ReserveAvailabilityHandler,
)
from app.application.commands.update_description import (
    UpdateDescriptionCommand,
    UpdateDescriptionHandler,
)
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
from app.domain.entity.base import BaseId
from app.presentation.schemas import (
    DescriptionCreateRequest,
    DescriptionUpdateRequest,
    EquipmentCreateRequest,
    EquipmentUpdateRequest,
    ImageCreateRequest,
    RequisiteCreateRequest,
    RequisiteUpdateRequest,
    ReserveAvailabilityRequest,
    SpareTimeCreateRequest,
)

router = APIRouter(tags=["web"], route_class=DishkaRoute)


@router.post("/users/{user_id}/description", status_code=201)
async def create_description(
    user_id: UUID,
    payload: DescriptionCreateRequest,
    handler: FromDishka[CreateDescriptionHandler],
) -> None:
    command = CreateDescriptionCommand(
        user_id=BaseId(user_id),
        username=payload.username,
        phone=payload.phone,
    )
    await handler(command)


@router.put("/users/{user_id}/description/{description_id}", status_code=204)
async def update_description(
    user_id: UUID,
    description_id: UUID,
    payload: DescriptionUpdateRequest,
    handler: FromDishka[UpdateDescriptionHandler],
) -> None:
    command = UpdateDescriptionCommand(
        user_id=BaseId(user_id),
        description_id=BaseId(description_id),
        username=payload.username,
        phone=payload.phone,
    )
    await handler(command)


@router.post("/users/{user_id}/spare-times", status_code=201)
async def add_spare_time(
    user_id: UUID,
    payload: SpareTimeCreateRequest,
    handler: FromDishka[AddSpareTimeHandler],
) -> None:
    command = AddSpareTimeCommand(
        user_id=BaseId(user_id),
        start_time=payload.start_time,
        end_time=payload.end_time,
    )
    await handler(command)


@router.post("/users/{user_id}/availability/reserve", status_code=200)
async def reserve_availability(
    user_id: UUID,
    payload: ReserveAvailabilityRequest,
    handler: FromDishka[ReserveAvailabilityHandler],
) -> None:
    command = ReserveAvailabilityCommand(
        user_id=BaseId(user_id),
        owner_id=BaseId(payload.owner_id),
        obj_id=BaseId(payload.obj_id),
        start_time=payload.start_time,
        end_time=payload.end_time,
    )
    await handler(command)


@router.post("/users/{user_id}/microfons", status_code=201)
async def create_microfon(
    user_id: UUID,
    payload: EquipmentCreateRequest,
    handler: FromDishka[CreateMicrofonHandler],
) -> None:
    command = CreateMicrofonCommand(
        user_id=BaseId(user_id),
        title=payload.title,
        description=payload.description,
        type=payload.type,
    )
    await handler(command)


@router.put("/users/{user_id}/microfons/{microfon_id}", status_code=204)
async def update_microfon(
    user_id: UUID,
    microfon_id: UUID,
    payload: EquipmentUpdateRequest,
    handler: FromDishka[UpdateMicrofonHandler],
) -> None:
    command = UpdateMicrofonCommand(
        user_id=BaseId(user_id),
        microfon_id=BaseId(microfon_id),
        title=payload.title,
        description=payload.description,
        type=payload.type,
    )
    await handler(command)


@router.delete("/users/{user_id}/microfons/{microfon_id}", status_code=204)
async def delete_microfon(
    user_id: UUID,
    microfon_id: UUID,
    handler: FromDishka[DeleteMicrofonHandler],
) -> None:
    command = DeleteMicrofonCommand(
        user_id=BaseId(user_id),
        microfon_id=BaseId(microfon_id),
    )
    await handler(command)


@router.post("/users/{user_id}/cameras", status_code=201)
async def create_camera(
    user_id: UUID,
    payload: EquipmentCreateRequest,
    handler: FromDishka[CreateCameraHandler],
) -> None:
    command = CreateCameraCommand(
        user_id=BaseId(user_id),
        title=payload.title,
        description=payload.description,
        type=payload.type,
    )
    await handler(command)


@router.put("/users/{user_id}/cameras/{camera_id}", status_code=204)
async def update_camera(
    user_id: UUID,
    camera_id: UUID,
    payload: EquipmentUpdateRequest,
    handler: FromDishka[UpdateCameraHandler],
) -> None:
    command = UpdateCameraCommand(
        user_id=BaseId(user_id),
        camera_id=BaseId(camera_id),
        title=payload.title,
        description=payload.description,
        type=payload.type,
    )
    await handler(command)


@router.delete("/users/{user_id}/cameras/{camera_id}", status_code=204)
async def delete_camera(
    user_id: UUID,
    camera_id: UUID,
    handler: FromDishka[DeleteCameraHandler],
) -> None:
    command = DeleteCameraCommand(
        user_id=BaseId(user_id),
        camera_id=BaseId(camera_id),
    )
    await handler(command)


@router.post("/users/{user_id}/camera-tripods", status_code=201)
async def create_camera_tripod(
    user_id: UUID,
    payload: EquipmentCreateRequest,
    handler: FromDishka[CreateCameraTripodHandler],
) -> None:
    command = CreateCameraTripodCommand(
        user_id=BaseId(user_id),
        title=payload.title,
        description=payload.description,
        type=payload.type,
    )
    await handler(command)


@router.put("/users/{user_id}/camera-tripods/{camera_tripod_id}", status_code=204)
async def update_camera_tripod(
    user_id: UUID,
    camera_tripod_id: UUID,
    payload: EquipmentUpdateRequest,
    handler: FromDishka[UpdateCameraTripodHandler],
) -> None:
    command = UpdateCameraTripodCommand(
        user_id=BaseId(user_id),
        camera_tripod_id=BaseId(camera_tripod_id),
        title=payload.title,
        description=payload.description,
        type=payload.type,
    )
    await handler(command)


@router.delete("/users/{user_id}/camera-tripods/{camera_tripod_id}", status_code=204)
async def delete_camera_tripod(
    user_id: UUID,
    camera_tripod_id: UUID,
    handler: FromDishka[DeleteCameraTripodHandler],
) -> None:
    command = DeleteCameraTripodCommand(
        user_id=BaseId(user_id),
        camera_tripod_id=BaseId(camera_tripod_id),
    )
    await handler(command)


@router.post("/users/{user_id}/lights", status_code=201)
async def create_light(
    user_id: UUID,
    payload: EquipmentCreateRequest,
    handler: FromDishka[CreateLightHandler],
) -> None:
    command = CreateLightCommand(
        user_id=BaseId(user_id),
        title=payload.title,
        description=payload.description,
        type=payload.type,
    )
    await handler(command)


@router.put("/users/{user_id}/lights/{light_id}", status_code=204)
async def update_light(
    user_id: UUID,
    light_id: UUID,
    payload: EquipmentUpdateRequest,
    handler: FromDishka[UpdateLightHandler],
) -> None:
    command = UpdateLightCommand(
        user_id=BaseId(user_id),
        light_id=BaseId(light_id),
        title=payload.title,
        description=payload.description,
        type=payload.type,
    )
    await handler(command)


@router.delete("/users/{user_id}/lights/{light_id}", status_code=204)
async def delete_light(
    user_id: UUID,
    light_id: UUID,
    handler: FromDishka[DeleteLightHandler],
) -> None:
    command = DeleteLightCommand(
        user_id=BaseId(user_id),
        light_id=BaseId(light_id),
    )
    await handler(command)


@router.post("/users/{user_id}/light-tripods", status_code=201)
async def create_light_tripod(
    user_id: UUID,
    payload: EquipmentCreateRequest,
    handler: FromDishka[CreateLightTripodHandler],
) -> None:
    command = CreateLightTripodCommand(
        user_id=BaseId(user_id),
        title=payload.title,
        description=payload.description,
        type=payload.type,
    )
    await handler(command)


@router.put("/users/{user_id}/light-tripods/{light_tripod_id}", status_code=204)
async def update_light_tripod(
    user_id: UUID,
    light_tripod_id: UUID,
    payload: EquipmentUpdateRequest,
    handler: FromDishka[UpdateLightTripodHandler],
) -> None:
    command = UpdateLightTripodCommand(
        user_id=BaseId(user_id),
        light_tripod_id=BaseId(light_tripod_id),
        title=payload.title,
        description=payload.description,
        type=payload.type,
    )
    await handler(command)


@router.delete("/users/{user_id}/light-tripods/{light_tripod_id}", status_code=204)
async def delete_light_tripod(
    user_id: UUID,
    light_tripod_id: UUID,
    handler: FromDishka[DeleteLightTripodHandler],
) -> None:
    command = DeleteLightTripodCommand(
        user_id=BaseId(user_id),
        light_tripod_id=BaseId(light_tripod_id),
    )
    await handler(command)


@router.post("/users/{user_id}/sounds", status_code=201)
async def create_sound(
    user_id: UUID,
    payload: EquipmentCreateRequest,
    handler: FromDishka[CreateSoundHandler],
) -> None:
    command = CreateSoundCommand(
        user_id=BaseId(user_id),
        title=payload.title,
        description=payload.description,
        type=payload.type,
    )
    await handler(command)


@router.put("/users/{user_id}/sounds/{sound_id}", status_code=204)
async def update_sound(
    user_id: UUID,
    sound_id: UUID,
    payload: EquipmentUpdateRequest,
    handler: FromDishka[UpdateSoundHandler],
) -> None:
    command = UpdateSoundCommand(
        user_id=BaseId(user_id),
        sound_id=BaseId(sound_id),
        title=payload.title,
        description=payload.description,
        type=payload.type,
    )
    await handler(command)


@router.delete("/users/{user_id}/sounds/{sound_id}", status_code=204)
async def delete_sound(
    user_id: UUID,
    sound_id: UUID,
    handler: FromDishka[DeleteSoundHandler],
) -> None:
    command = DeleteSoundCommand(
        user_id=BaseId(user_id),
        sound_id=BaseId(sound_id),
    )
    await handler(command)


@router.post("/users/{user_id}/requisites", status_code=201)
async def create_requisite(
    user_id: UUID,
    payload: RequisiteCreateRequest,
    handler: FromDishka[CreateRequisiteHandler],
) -> None:
    command = CreateRequisiteCommand(
        user_id=BaseId(user_id),
        title=payload.title,
        description=payload.description,
        type=payload.type,
        size=payload.size,
    )
    await handler(command)


@router.put("/users/{user_id}/requisites/{requisite_id}", status_code=204)
async def update_requisite(
    user_id: UUID,
    requisite_id: UUID,
    payload: RequisiteUpdateRequest,
    handler: FromDishka[UpdateRequisiteHandler],
) -> None:
    command = UpdateRequisiteCommand(
        user_id=BaseId(user_id),
        requisite_id=BaseId(requisite_id),
        title=payload.title,
        description=payload.description,
        type=payload.type,
        size=payload.size,
    )
    await handler(command)


@router.delete("/users/{user_id}/requisites/{requisite_id}", status_code=204)
async def delete_requisite(
    user_id: UUID,
    requisite_id: UUID,
    handler: FromDishka[DeleteRequisiteHandler],
) -> None:
    command = DeleteRequisiteCommand(
        user_id=BaseId(user_id),
        requisite_id=BaseId(requisite_id),
    )
    await handler(command)


@router.post("/users/{user_id}/requisites/{requisite_id}/images", status_code=201)
async def add_image(
    user_id: UUID,
    requisite_id: UUID,
    payload: ImageCreateRequest,
    handler: FromDishka[AddImageHandler],
) -> None:
    command = AddImageCommand(
        user_id=BaseId(user_id),
        requisite_id=BaseId(requisite_id),
        file=payload.file,
        title=payload.title,
        storage_key=payload.storage_key,
        bucket=payload.bucket,
        mime_type=payload.mime_type,
        size=payload.size,
        description=payload.description,
    )
    await handler(command)


@router.delete(
    "/users/{user_id}/requisites/{requisite_id}/images/{image_id}",
    status_code=204,
)
async def remove_image(
    user_id: UUID,
    requisite_id: UUID,
    image_id: UUID,
    handler: FromDishka[RemoveImageHandler],
) -> None:
    command = RemoveImageCommand(
        user_id=BaseId(user_id),
        requisite_id=BaseId(requisite_id),
        image_id=BaseId(image_id),
    )
    await handler(command)
