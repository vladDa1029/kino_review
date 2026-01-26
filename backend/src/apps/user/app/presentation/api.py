from uuid import UUID

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Depends, Header, HTTPException, status

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


def user_id_from_header(
    user_id: UUID,
    x_user_id: UUID | None = Header(default=None, alias="x-user-id"),
) -> BaseId:
    if x_user_id is None:
        return BaseId(user_id)
    if x_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="x-user-id does not match path user_id.",
        )
    return BaseId(x_user_id)


@router.post("/users/{user_id}/description", status_code=201)
async def create_description(
    payload: DescriptionCreateRequest,
    handler: FromDishka[CreateDescriptionHandler],
    user_id: BaseId = Depends(user_id_from_header),
) -> None:
    command = CreateDescriptionCommand(
        user_id=user_id,
        username=payload.username,
        phone=payload.phone,
    )
    await handler(command)


@router.put("/users/{user_id}/description/{description_id}", status_code=204)
async def update_description(
    description_id: UUID,
    payload: DescriptionUpdateRequest,
    handler: FromDishka[UpdateDescriptionHandler],
    user_id: BaseId = Depends(user_id_from_header),
) -> None:
    command = UpdateDescriptionCommand(
        user_id=user_id,
        description_id=BaseId(description_id),
        username=payload.username,
        phone=payload.phone,
    )
    await handler(command)


@router.post("/users/{user_id}/spare-times", status_code=201)
async def add_spare_time(
    payload: SpareTimeCreateRequest,
    handler: FromDishka[AddSpareTimeHandler],
    user_id: BaseId = Depends(user_id_from_header),
) -> None:
    command = AddSpareTimeCommand(
        user_id=user_id,
        start_time=payload.start_time,
        end_time=payload.end_time,
    )
    await handler(command)


@router.post("/users/{user_id}/availability/reserve", status_code=200)
async def reserve_availability(
    payload: ReserveAvailabilityRequest,
    handler: FromDishka[ReserveAvailabilityHandler],
    user_id: BaseId = Depends(user_id_from_header),
) -> None:
    command = ReserveAvailabilityCommand(
        user_id=user_id,
        owner_id=BaseId(payload.owner_id),
        obj_id=BaseId(payload.obj_id),
        start_time=payload.start_time,
        end_time=payload.end_time,
    )
    await handler(command)


@router.post("/users/{user_id}/microfons", status_code=201)
async def create_microfon(
    payload: EquipmentCreateRequest,
    handler: FromDishka[CreateMicrofonHandler],
    user_id: BaseId = Depends(user_id_from_header),
) -> None:
    command = CreateMicrofonCommand(
        user_id=user_id,
        title=payload.title,
        description=payload.description,
        type=payload.type,
    )
    await handler(command)


@router.put("/users/{user_id}/microfons/{microfon_id}", status_code=204)
async def update_microfon(
    microfon_id: UUID,
    payload: EquipmentUpdateRequest,
    handler: FromDishka[UpdateMicrofonHandler],
    user_id: BaseId = Depends(user_id_from_header),
) -> None:
    command = UpdateMicrofonCommand(
        user_id=user_id,
        microfon_id=BaseId(microfon_id),
        title=payload.title,
        description=payload.description,
        type=payload.type,
    )
    await handler(command)


@router.delete("/users/{user_id}/microfons/{microfon_id}", status_code=204)
async def delete_microfon(
    microfon_id: UUID,
    handler: FromDishka[DeleteMicrofonHandler],
    user_id: BaseId = Depends(user_id_from_header),
) -> None:
    command = DeleteMicrofonCommand(
        user_id=user_id,
        microfon_id=BaseId(microfon_id),
    )
    await handler(command)


@router.post("/users/{user_id}/cameras", status_code=201)
async def create_camera(
    payload: EquipmentCreateRequest,
    handler: FromDishka[CreateCameraHandler],
    user_id: BaseId = Depends(user_id_from_header),
) -> None:
    command = CreateCameraCommand(
        user_id=user_id,
        title=payload.title,
        description=payload.description,
        type=payload.type,
    )
    await handler(command)


@router.put("/users/{user_id}/cameras/{camera_id}", status_code=204)
async def update_camera(
    camera_id: UUID,
    payload: EquipmentUpdateRequest,
    handler: FromDishka[UpdateCameraHandler],
    user_id: BaseId = Depends(user_id_from_header),
) -> None:
    command = UpdateCameraCommand(
        user_id=user_id,
        camera_id=BaseId(camera_id),
        title=payload.title,
        description=payload.description,
        type=payload.type,
    )
    await handler(command)


@router.delete("/users/{user_id}/cameras/{camera_id}", status_code=204)
async def delete_camera(
    camera_id: UUID,
    handler: FromDishka[DeleteCameraHandler],
    user_id: BaseId = Depends(user_id_from_header),
) -> None:
    command = DeleteCameraCommand(
        user_id=user_id,
        camera_id=BaseId(camera_id),
    )
    await handler(command)


@router.post("/users/{user_id}/camera-tripods", status_code=201)
async def create_camera_tripod(
    payload: EquipmentCreateRequest,
    handler: FromDishka[CreateCameraTripodHandler],
    user_id: BaseId = Depends(user_id_from_header),
) -> None:
    command = CreateCameraTripodCommand(
        user_id=user_id,
        title=payload.title,
        description=payload.description,
        type=payload.type,
    )
    await handler(command)


@router.put("/users/{user_id}/camera-tripods/{camera_tripod_id}", status_code=204)
async def update_camera_tripod(
    camera_tripod_id: UUID,
    payload: EquipmentUpdateRequest,
    handler: FromDishka[UpdateCameraTripodHandler],
    user_id: BaseId = Depends(user_id_from_header),
) -> None:
    command = UpdateCameraTripodCommand(
        user_id=user_id,
        camera_tripod_id=BaseId(camera_tripod_id),
        title=payload.title,
        description=payload.description,
        type=payload.type,
    )
    await handler(command)


@router.delete("/users/{user_id}/camera-tripods/{camera_tripod_id}", status_code=204)
async def delete_camera_tripod(
    camera_tripod_id: UUID,
    handler: FromDishka[DeleteCameraTripodHandler],
    user_id: BaseId = Depends(user_id_from_header),
) -> None:
    command = DeleteCameraTripodCommand(
        user_id=user_id,
        camera_tripod_id=BaseId(camera_tripod_id),
    )
    await handler(command)


@router.post("/users/{user_id}/lights", status_code=201)
async def create_light(
    payload: EquipmentCreateRequest,
    handler: FromDishka[CreateLightHandler],
    user_id: BaseId = Depends(user_id_from_header),
) -> None:
    command = CreateLightCommand(
        user_id=user_id,
        title=payload.title,
        description=payload.description,
        type=payload.type,
    )
    await handler(command)


@router.put("/users/{user_id}/lights/{light_id}", status_code=204)
async def update_light(
    light_id: UUID,
    payload: EquipmentUpdateRequest,
    handler: FromDishka[UpdateLightHandler],
    user_id: BaseId = Depends(user_id_from_header),
) -> None:
    command = UpdateLightCommand(
        user_id=user_id,
        light_id=BaseId(light_id),
        title=payload.title,
        description=payload.description,
        type=payload.type,
    )
    await handler(command)


@router.delete("/users/{user_id}/lights/{light_id}", status_code=204)
async def delete_light(
    light_id: UUID,
    handler: FromDishka[DeleteLightHandler],
    user_id: BaseId = Depends(user_id_from_header),
) -> None:
    command = DeleteLightCommand(
        user_id=user_id,
        light_id=BaseId(light_id),
    )
    await handler(command)


@router.post("/users/{user_id}/light-tripods", status_code=201)
async def create_light_tripod(
    payload: EquipmentCreateRequest,
    handler: FromDishka[CreateLightTripodHandler],
    user_id: BaseId = Depends(user_id_from_header),
) -> None:
    command = CreateLightTripodCommand(
        user_id=user_id,
        title=payload.title,
        description=payload.description,
        type=payload.type,
    )
    await handler(command)


@router.put("/users/{user_id}/light-tripods/{light_tripod_id}", status_code=204)
async def update_light_tripod(
    light_tripod_id: UUID,
    payload: EquipmentUpdateRequest,
    handler: FromDishka[UpdateLightTripodHandler],
    user_id: BaseId = Depends(user_id_from_header),
) -> None:
    command = UpdateLightTripodCommand(
        user_id=user_id,
        light_tripod_id=BaseId(light_tripod_id),
        title=payload.title,
        description=payload.description,
        type=payload.type,
    )
    await handler(command)


@router.delete("/users/{user_id}/light-tripods/{light_tripod_id}", status_code=204)
async def delete_light_tripod(
    light_tripod_id: UUID,
    handler: FromDishka[DeleteLightTripodHandler],
    user_id: BaseId = Depends(user_id_from_header),
) -> None:
    command = DeleteLightTripodCommand(
        user_id=user_id,
        light_tripod_id=BaseId(light_tripod_id),
    )
    await handler(command)


@router.post("/users/{user_id}/sounds", status_code=201)
async def create_sound(
    payload: EquipmentCreateRequest,
    handler: FromDishka[CreateSoundHandler],
    user_id: BaseId = Depends(user_id_from_header),
) -> None:
    command = CreateSoundCommand(
        user_id=user_id,
        title=payload.title,
        description=payload.description,
        type=payload.type,
    )
    await handler(command)


@router.put("/users/{user_id}/sounds/{sound_id}", status_code=204)
async def update_sound(
    sound_id: UUID,
    payload: EquipmentUpdateRequest,
    handler: FromDishka[UpdateSoundHandler],
    user_id: BaseId = Depends(user_id_from_header),
) -> None:
    command = UpdateSoundCommand(
        user_id=user_id,
        sound_id=BaseId(sound_id),
        title=payload.title,
        description=payload.description,
        type=payload.type,
    )
    await handler(command)


@router.delete("/users/{user_id}/sounds/{sound_id}", status_code=204)
async def delete_sound(
    sound_id: UUID,
    handler: FromDishka[DeleteSoundHandler],
    user_id: BaseId = Depends(user_id_from_header),
) -> None:
    command = DeleteSoundCommand(
        user_id=user_id,
        sound_id=BaseId(sound_id),
    )
    await handler(command)


@router.post("/users/{user_id}/requisites", status_code=201)
async def create_requisite(
    payload: RequisiteCreateRequest,
    handler: FromDishka[CreateRequisiteHandler],
    user_id: BaseId = Depends(user_id_from_header),
) -> None:
    command = CreateRequisiteCommand(
        user_id=user_id,
        title=payload.title,
        description=payload.description,
        type=payload.type,
        size=payload.size,
    )
    await handler(command)


@router.put("/users/{user_id}/requisites/{requisite_id}", status_code=204)
async def update_requisite(
    requisite_id: UUID,
    payload: RequisiteUpdateRequest,
    handler: FromDishka[UpdateRequisiteHandler],
    user_id: BaseId = Depends(user_id_from_header),
) -> None:
    command = UpdateRequisiteCommand(
        user_id=user_id,
        requisite_id=BaseId(requisite_id),
        title=payload.title,
        description=payload.description,
        type=payload.type,
        size=payload.size,
    )
    await handler(command)


@router.delete("/users/{user_id}/requisites/{requisite_id}", status_code=204)
async def delete_requisite(
    requisite_id: UUID,
    handler: FromDishka[DeleteRequisiteHandler],
    user_id: BaseId = Depends(user_id_from_header),
) -> None:
    command = DeleteRequisiteCommand(
        user_id=user_id,
        requisite_id=BaseId(requisite_id),
    )
    await handler(command)


@router.post("/users/{user_id}/requisites/{requisite_id}/images", status_code=201)
async def add_image(
    requisite_id: UUID,
    payload: ImageCreateRequest,
    handler: FromDishka[AddImageHandler],
    user_id: BaseId = Depends(user_id_from_header),
) -> None:
    command = AddImageCommand(
        user_id=user_id,
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
    requisite_id: UUID,
    image_id: UUID,
    handler: FromDishka[RemoveImageHandler],
    user_id: BaseId = Depends(user_id_from_header),
) -> None:
    command = RemoveImageCommand(
        user_id=user_id,
        requisite_id=BaseId(requisite_id),
        image_id=BaseId(image_id),
    )
    await handler(command)
