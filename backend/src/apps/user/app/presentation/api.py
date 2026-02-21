import math
from uuid import UUID

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile, status

from app.application.commands.add_image import AddImageCommand, AddImageHandler
from app.application.commands.add_equipment_free_time import (
    AddCameraFreeTimeCommand,
    AddCameraFreeTimeHandler,
    AddCameraTripodFreeTimeCommand,
    AddCameraTripodFreeTimeHandler,
    AddLightFreeTimeCommand,
    AddLightFreeTimeHandler,
    AddLightTripodFreeTimeCommand,
    AddLightTripodFreeTimeHandler,
    AddMicrofonFreeTimeCommand,
    AddMicrofonFreeTimeHandler,
    AddRequisiteFreeTimeCommand,
    AddRequisiteFreeTimeHandler,
    AddSoundFreeTimeCommand,
    AddSoundFreeTimeHandler,
)
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
from app.application.common import EquipmentFilters, EquipmentSorting, Pagination
from app.application.queries.images import (
    GetRequisiteImageHandler,
    GetRequisiteImageQuery,
    ListRequisiteImagesHandler,
    ListRequisiteImagesQuery,
)
from app.application.queries.list_equipment import (
    ListCamerasHandler,
    ListCameraTripodsHandler,
    ListEquipmentQuery,
    ListLightsHandler,
    ListLightTripodsHandler,
    ListMicrofonsHandler,
    ListRequisitesHandler,
    ListSoundsHandler,
)
from app.domain.entity.base import BaseId
from app.application.ports.storage import FileStorage
from app.config import ImageSettings
from app.presentation.schemas import (
    DescriptionCreateRequest,
    DescriptionUpdateRequest,
    EquipmentItemResponse,
    EquipmentListQuery,
    EquipmentListResponse,
    EquipmentCreateRequest,
    EquipmentUpdateRequest,
    ImageListResponse,
    ImageResponse,
    RequisiteItemResponse,
    RequisiteListQuery,
    RequisiteListResponse,
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


def _build_pagination(page: int, page_size: int) -> Pagination:
    return Pagination(page=page, page_size=page_size)


def _build_pages(total_count: int, page_size: int) -> int:
    return math.ceil(total_count / page_size)


def _build_sorting(
    sort_by: str | None,
    sort_dir: str,
) -> EquipmentSorting | None:
    if sort_by is None:
        return None
    return EquipmentSorting(field=sort_by, direction=sort_dir)


def _equipment_filters(
    user_id: BaseId,
    params: EquipmentListQuery,
) -> EquipmentFilters:
    return EquipmentFilters(
        user_id=user_id,
        type=params.type,
        search=params.search,
        created_from=params.created_from,
        created_to=params.created_to,
    )


def _requisite_filters(
    user_id: BaseId,
    params: RequisiteListQuery,
) -> EquipmentFilters:
    return EquipmentFilters(
        user_id=user_id,
        type=params.type,
        size=params.size,
        search=params.search,
        created_from=params.created_from,
        created_to=params.created_to,
    )


def _equipment_response(item) -> EquipmentItemResponse:
    return EquipmentItemResponse(
        oid=item.oid,
        user_id=item.users_id,
        title=item.title,
        description=item.description,
        type=item.type,
        create_at=item.create_at,
    )


def _requisite_response(item) -> RequisiteItemResponse:
    return RequisiteItemResponse(
        oid=item.oid,
        user_id=item.users_id,
        title=item.title,
        description=item.description,
        type=item.type,
        size=item.size,
        create_at=item.create_at,
    )


def _image_response(item) -> ImageResponse:
    return ImageResponse(
        oid=item.oid,
        requisite_id=item.requisite_id,
        file=item.file,
        title=item.title,
        storage_key=item.storage_key,
        bucket=item.bucket,
        mime_type=item.mime_type,
        size=item.size,
        description=item.description,
        create_at=item.create_at,
    )


def _validate_image_upload(
    file: UploadFile,
    data: bytes,
    settings: ImageSettings,
) -> None:
    if file.content_type is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing content type.",
        )
    if file.content_type not in settings.allowed_mime_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported image type.",
        )
    if len(data) > settings.max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image size exceeds limit.",
        )


@router.post(
    "/users/{user_id}/description",
    status_code=201,
    summary="Create user description",
    description="Creates a single description record for the user.",
)
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


@router.put(
    "/users/{user_id}/description/{description_id}",
    status_code=204,
    summary="Update user description",
    description="Updates the existing user description.",
)
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


@router.post(
    "/users/{user_id}/spare-times",
    status_code=201,
    summary="Add user free time window",
    description="Adds a free time window for the user.",
)
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


@router.post(
    "/users/{user_id}/microfons/{microfon_id}/free-times",
    status_code=201,
    summary="Add microfon free time",
    description="Adds a free time window for the specified microfon.",
)
async def add_microfon_free_time(
    microfon_id: UUID,
    payload: SpareTimeCreateRequest,
    handler: FromDishka[AddMicrofonFreeTimeHandler],
    user_id: BaseId = Depends(user_id_from_header),
) -> None:
    command = AddMicrofonFreeTimeCommand(
        user_id=user_id,
        microfon_id=BaseId(microfon_id),
        start_time=payload.start_time,
        end_time=payload.end_time,
    )
    await handler(command)


@router.post(
    "/users/{user_id}/cameras/{camera_id}/free-times",
    status_code=201,
    summary="Add camera free time",
    description="Adds a free time window for the specified camera.",
)
async def add_camera_free_time(
    camera_id: UUID,
    payload: SpareTimeCreateRequest,
    handler: FromDishka[AddCameraFreeTimeHandler],
    user_id: BaseId = Depends(user_id_from_header),
) -> None:
    command = AddCameraFreeTimeCommand(
        user_id=user_id,
        camera_id=BaseId(camera_id),
        start_time=payload.start_time,
        end_time=payload.end_time,
    )
    await handler(command)


@router.post(
    "/users/{user_id}/camera-tripods/{camera_tripod_id}/free-times",
    status_code=201,
    summary="Add camera tripod free time",
    description="Adds a free time window for the specified camera tripod.",
)
async def add_camera_tripod_free_time(
    camera_tripod_id: UUID,
    payload: SpareTimeCreateRequest,
    handler: FromDishka[AddCameraTripodFreeTimeHandler],
    user_id: BaseId = Depends(user_id_from_header),
) -> None:
    command = AddCameraTripodFreeTimeCommand(
        user_id=user_id,
        camera_tripod_id=BaseId(camera_tripod_id),
        start_time=payload.start_time,
        end_time=payload.end_time,
    )
    await handler(command)


@router.post(
    "/users/{user_id}/lights/{light_id}/free-times",
    status_code=201,
    summary="Add light free time",
    description="Adds a free time window for the specified light.",
)
async def add_light_free_time(
    light_id: UUID,
    payload: SpareTimeCreateRequest,
    handler: FromDishka[AddLightFreeTimeHandler],
    user_id: BaseId = Depends(user_id_from_header),
) -> None:
    command = AddLightFreeTimeCommand(
        user_id=user_id,
        light_id=BaseId(light_id),
        start_time=payload.start_time,
        end_time=payload.end_time,
    )
    await handler(command)


@router.post(
    "/users/{user_id}/light-tripods/{light_tripod_id}/free-times",
    status_code=201,
    summary="Add light tripod free time",
    description="Adds a free time window for the specified light tripod.",
)
async def add_light_tripod_free_time(
    light_tripod_id: UUID,
    payload: SpareTimeCreateRequest,
    handler: FromDishka[AddLightTripodFreeTimeHandler],
    user_id: BaseId = Depends(user_id_from_header),
) -> None:
    command = AddLightTripodFreeTimeCommand(
        user_id=user_id,
        light_tripod_id=BaseId(light_tripod_id),
        start_time=payload.start_time,
        end_time=payload.end_time,
    )
    await handler(command)


@router.post(
    "/users/{user_id}/sounds/{sound_id}/free-times",
    status_code=201,
    summary="Add sound free time",
    description="Adds a free time window for the specified sound.",
)
async def add_sound_free_time(
    sound_id: UUID,
    payload: SpareTimeCreateRequest,
    handler: FromDishka[AddSoundFreeTimeHandler],
    user_id: BaseId = Depends(user_id_from_header),
) -> None:
    command = AddSoundFreeTimeCommand(
        user_id=user_id,
        sound_id=BaseId(sound_id),
        start_time=payload.start_time,
        end_time=payload.end_time,
    )
    await handler(command)


@router.post(
    "/users/{user_id}/requisites/{requisite_id}/free-times",
    status_code=201,
    summary="Add requisite free time",
    description="Adds a free time window for the specified requisite.",
)
async def add_requisite_free_time(
    requisite_id: UUID,
    payload: SpareTimeCreateRequest,
    handler: FromDishka[AddRequisiteFreeTimeHandler],
    user_id: BaseId = Depends(user_id_from_header),
) -> None:
    command = AddRequisiteFreeTimeCommand(
        user_id=user_id,
        requisite_id=BaseId(requisite_id),
        start_time=payload.start_time,
        end_time=payload.end_time,
    )
    await handler(command)


@router.post(
    "/users/{user_id}/availability/reserve",
    status_code=200,
    summary="Reserve availability window",
    description="Reserves a time window within existing availability.",
)
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


@router.post(
    "/users/{user_id}/microfons",
    status_code=201,
    summary="Create microfon",
    description="Creates a new microfon owned by the user.",
)
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


@router.put(
    "/users/{user_id}/microfons/{microfon_id}",
    status_code=204,
    summary="Update microfon",
    description="Updates the specified microfon.",
)
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


@router.delete(
    "/users/{user_id}/microfons/{microfon_id}",
    status_code=204,
    summary="Delete microfon",
    description="Deletes the specified microfon.",
)
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


@router.post(
    "/users/{user_id}/cameras",
    status_code=201,
    summary="Create camera",
    description="Creates a new camera owned by the user.",
)
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


@router.put(
    "/users/{user_id}/cameras/{camera_id}",
    status_code=204,
    summary="Update camera",
    description="Updates the specified camera.",
)
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


@router.delete(
    "/users/{user_id}/cameras/{camera_id}",
    status_code=204,
    summary="Delete camera",
    description="Deletes the specified camera.",
)
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


@router.post(
    "/users/{user_id}/camera-tripods",
    status_code=201,
    summary="Create camera tripod",
    description="Creates a new camera tripod owned by the user.",
)
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


@router.put(
    "/users/{user_id}/camera-tripods/{camera_tripod_id}",
    status_code=204,
    summary="Update camera tripod",
    description="Updates the specified camera tripod.",
)
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


@router.delete(
    "/users/{user_id}/camera-tripods/{camera_tripod_id}",
    status_code=204,
    summary="Delete camera tripod",
    description="Deletes the specified camera tripod.",
)
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


@router.post(
    "/users/{user_id}/lights",
    status_code=201,
    summary="Create light",
    description="Creates a new light owned by the user.",
)
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


@router.put(
    "/users/{user_id}/lights/{light_id}",
    status_code=204,
    summary="Update light",
    description="Updates the specified light.",
)
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


@router.delete(
    "/users/{user_id}/lights/{light_id}",
    status_code=204,
    summary="Delete light",
    description="Deletes the specified light.",
)
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


@router.post(
    "/users/{user_id}/light-tripods",
    status_code=201,
    summary="Create light tripod",
    description="Creates a new light tripod owned by the user.",
)
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


@router.put(
    "/users/{user_id}/light-tripods/{light_tripod_id}",
    status_code=204,
    summary="Update light tripod",
    description="Updates the specified light tripod.",
)
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


@router.delete(
    "/users/{user_id}/light-tripods/{light_tripod_id}",
    status_code=204,
    summary="Delete light tripod",
    description="Deletes the specified light tripod.",
)
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


@router.post(
    "/users/{user_id}/sounds",
    status_code=201,
    summary="Create sound",
    description="Creates a new sound owned by the user.",
)
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


@router.put(
    "/users/{user_id}/sounds/{sound_id}",
    status_code=204,
    summary="Update sound",
    description="Updates the specified sound.",
)
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


@router.delete(
    "/users/{user_id}/sounds/{sound_id}",
    status_code=204,
    summary="Delete sound",
    description="Deletes the specified sound.",
)
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


@router.post(
    "/users/{user_id}/requisites",
    status_code=201,
    summary="Create requisite",
    description="Creates a new requisite owned by the user.",
)
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


@router.put(
    "/users/{user_id}/requisites/{requisite_id}",
    status_code=204,
    summary="Update requisite",
    description="Updates the specified requisite.",
)
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


@router.delete(
    "/users/{user_id}/requisites/{requisite_id}",
    status_code=204,
    summary="Delete requisite",
    description="Deletes the specified requisite.",
)
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


@router.post(
    "/users/{user_id}/requisites/{requisite_id}/images",
    status_code=201,
    summary="Add image",
    description="Adds an image to the specified requisite.",
)
async def add_image(
    requisite_id: UUID,
    handler: FromDishka[AddImageHandler],
    storage: FromDishka[FileStorage],
    image_settings: FromDishka[ImageSettings],
    user_id: BaseId = Depends(user_id_from_header),
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str = Form(...),
) -> None:
    data = await file.read()
    _validate_image_upload(file, data, image_settings)
    stored = await storage.upload(
        data=data,
        key=f"{requisite_id}/{file.filename}",
        content_type=file.content_type,
    )
    command = AddImageCommand(
        user_id=user_id,
        requisite_id=BaseId(requisite_id),
        file=file.filename,
        title=title,
        storage_key=stored.key,
        bucket=stored.bucket,
        mime_type=file.content_type or "application/octet-stream",
        size=len(data),
        description=description,
    )
    await handler(command)


@router.get(
    "/users/{user_id}/requisites/{requisite_id}/images",
    response_model=ImageListResponse,
    summary="List images",
    description="Returns all images for the specified requisite.",
)
async def list_requisite_images(
    requisite_id: UUID,
    handler: FromDishka[ListRequisiteImagesHandler],
    user_id: BaseId = Depends(user_id_from_header),
) -> ImageListResponse:
    query = ListRequisiteImagesQuery(
        user_id=user_id,
        requisite_id=BaseId(requisite_id),
    )
    items = await handler(query)
    return ImageListResponse(items=[_image_response(item) for item in items])


@router.get(
    "/users/{user_id}/requisites/{requisite_id}/images/{image_id}",
    response_model=ImageResponse,
    summary="Get image",
    description="Returns an image metadata for the specified requisite.",
)
async def get_requisite_image(
    requisite_id: UUID,
    image_id: UUID,
    handler: FromDishka[GetRequisiteImageHandler],
    user_id: BaseId = Depends(user_id_from_header),
) -> ImageResponse:
    query = GetRequisiteImageQuery(
        user_id=user_id,
        requisite_id=BaseId(requisite_id),
        image_id=BaseId(image_id),
    )
    item = await handler(query)
    return _image_response(item)


@router.delete(
    "/users/{user_id}/requisites/{requisite_id}/images/{image_id}",
    status_code=204,
    summary="Remove image",
    description="Removes an image from the specified requisite.",
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


@router.get(
    "/users/{user_id}/microfons",
    response_model=EquipmentListResponse,
    summary="List microfons",
    description="Returns a paginated list of microfons.",
)
async def list_microfons(
    handler: FromDishka[ListMicrofonsHandler],
    params: EquipmentListQuery = Depends(),
    user_id: BaseId = Depends(user_id_from_header),
) -> EquipmentListResponse:
    pagination = _build_pagination(params.page, params.page_size)
    filters = _equipment_filters(user_id, params)
    sorting = _build_sorting(params.sort_by, params.sort_dir)
    query = ListEquipmentQuery(
        filters=filters,
        sorting=sorting,
        pagination=pagination,
    )
    result = await handler(query)
    return EquipmentListResponse(
        items=[_equipment_response(item) for item in result.items],
        page=params.page,
        page_size=params.page_size,
        total_count=result.total_count,
        pages=_build_pages(result.total_count, params.page_size),
    )


@router.get(
    "/users/{user_id}/cameras",
    response_model=EquipmentListResponse,
    summary="List cameras",
    description="Returns a paginated list of cameras.",
)
async def list_cameras(
    handler: FromDishka[ListCamerasHandler],
    params: EquipmentListQuery = Depends(),
    user_id: BaseId = Depends(user_id_from_header),
) -> EquipmentListResponse:
    pagination = _build_pagination(params.page, params.page_size)
    filters = _equipment_filters(user_id, params)
    sorting = _build_sorting(params.sort_by, params.sort_dir)
    query = ListEquipmentQuery(
        filters=filters,
        sorting=sorting,
        pagination=pagination,
    )
    result = await handler(query)
    return EquipmentListResponse(
        items=[_equipment_response(item) for item in result.items],
        page=params.page,
        page_size=params.page_size,
        total_count=result.total_count,
        pages=_build_pages(result.total_count, params.page_size),
    )


@router.get(
    "/users/{user_id}/camera-tripods",
    response_model=EquipmentListResponse,
    summary="List camera tripods",
    description="Returns a paginated list of camera tripods.",
)
async def list_camera_tripods(
    handler: FromDishka[ListCameraTripodsHandler],
    params: EquipmentListQuery = Depends(),
    user_id: BaseId = Depends(user_id_from_header),
) -> EquipmentListResponse:
    pagination = _build_pagination(params.page, params.page_size)
    filters = _equipment_filters(user_id, params)
    sorting = _build_sorting(params.sort_by, params.sort_dir)
    query = ListEquipmentQuery(
        filters=filters,
        sorting=sorting,
        pagination=pagination,
    )
    result = await handler(query)
    return EquipmentListResponse(
        items=[_equipment_response(item) for item in result.items],
        page=params.page,
        page_size=params.page_size,
        total_count=result.total_count,
        pages=_build_pages(result.total_count, params.page_size),
    )


@router.get(
    "/users/{user_id}/lights",
    response_model=EquipmentListResponse,
    summary="List lights",
    description="Returns a paginated list of lights.",
)
async def list_lights(
    handler: FromDishka[ListLightsHandler],
    params: EquipmentListQuery = Depends(),
    user_id: BaseId = Depends(user_id_from_header),
) -> EquipmentListResponse:
    pagination = _build_pagination(params.page, params.page_size)
    filters = _equipment_filters(user_id, params)
    sorting = _build_sorting(params.sort_by, params.sort_dir)
    query = ListEquipmentQuery(
        filters=filters,
        sorting=sorting,
        pagination=pagination,
    )
    result = await handler(query)
    return EquipmentListResponse(
        items=[_equipment_response(item) for item in result.items],
        page=params.page,
        page_size=params.page_size,
        total_count=result.total_count,
        pages=_build_pages(result.total_count, params.page_size),
    )


@router.get(
    "/users/{user_id}/light-tripods",
    response_model=EquipmentListResponse,
    summary="List light tripods",
    description="Returns a paginated list of light tripods.",
)
async def list_light_tripods(
    handler: FromDishka[ListLightTripodsHandler],
    params: EquipmentListQuery = Depends(),
    user_id: BaseId = Depends(user_id_from_header),
) -> EquipmentListResponse:
    pagination = _build_pagination(params.page, params.page_size)
    filters = _equipment_filters(user_id, params)
    sorting = _build_sorting(params.sort_by, params.sort_dir)
    query = ListEquipmentQuery(
        filters=filters,
        sorting=sorting,
        pagination=pagination,
    )
    result = await handler(query)
    return EquipmentListResponse(
        items=[_equipment_response(item) for item in result.items],
        page=params.page,
        page_size=params.page_size,
        total_count=result.total_count,
        pages=_build_pages(result.total_count, params.page_size),
    )


@router.get(
    "/users/{user_id}/sounds",
    response_model=EquipmentListResponse,
    summary="List sounds",
    description="Returns a paginated list of sounds.",
)
async def list_sounds(
    handler: FromDishka[ListSoundsHandler],
    params: EquipmentListQuery = Depends(),
    user_id: BaseId = Depends(user_id_from_header),
) -> EquipmentListResponse:
    pagination = _build_pagination(params.page, params.page_size)
    filters = _equipment_filters(user_id, params)
    sorting = _build_sorting(params.sort_by, params.sort_dir)
    query = ListEquipmentQuery(
        filters=filters,
        sorting=sorting,
        pagination=pagination,
    )
    result = await handler(query)
    return EquipmentListResponse(
        items=[_equipment_response(item) for item in result.items],
        page=params.page,
        page_size=params.page_size,
        total_count=result.total_count,
        pages=_build_pages(result.total_count, params.page_size),
    )


@router.get(
    "/users/{user_id}/requisites",
    response_model=RequisiteListResponse,
    summary="List requisites",
    description="Returns a paginated list of requisites.",
)
async def list_requisites(
    handler: FromDishka[ListRequisitesHandler],
    params: RequisiteListQuery = Depends(),
    user_id: BaseId = Depends(user_id_from_header),
) -> RequisiteListResponse:
    pagination = _build_pagination(params.page, params.page_size)
    filters = _requisite_filters(user_id, params)
    sorting = _build_sorting(params.sort_by, params.sort_dir)
    query = ListEquipmentQuery(
        filters=filters,
        sorting=sorting,
        pagination=pagination,
    )
    result = await handler(query)
    return RequisiteListResponse(
        items=[_requisite_response(item) for item in result.items],
        page=params.page,
        page_size=params.page_size,
        total_count=result.total_count,
        pages=_build_pages(result.total_count, params.page_size),
    )
