from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.application.common.pagination import MAX_PAGE_SIZE


class DescriptionCreateRequest(BaseModel):
    username: str = Field(examples=["Ivan Petrov"])
    phone: Annotated[str, Field(min_length=10, examples=["+79991234567"])]


class DescriptionUpdateRequest(BaseModel):
    username: str = Field(examples=["Ivan Petrov"])
    phone: str = Field(examples=["+79991234567"])


class SpareTimeCreateRequest(BaseModel):
    start_time: datetime = Field(examples=["2026-01-15T10:00:00Z"])
    end_time: datetime = Field(examples=["2026-01-15T18:00:00Z"])


class ReserveAvailabilityRequest(BaseModel):
    owner_id: UUID = Field(examples=["4a117f56-0f02-4d4d-9c25-51b2a778b6f6"])
    obj_id: UUID = Field(examples=["5f6a3b8f-3f68-4b15-9f1b-7f5c0b2f5c9a"])
    start_time: datetime = Field(examples=["2026-01-15T10:00:00Z"])
    end_time: datetime = Field(examples=["2026-01-15T12:00:00Z"])


class EquipmentCreateRequest(BaseModel):
    title: str = Field(examples=["Sony A7S III"])
    description: str = Field(examples=["Full-frame mirrorless camera"])
    type: str = Field(examples=["mirrorless"])


class EquipmentUpdateRequest(BaseModel):
    title: str = Field(examples=["Sony A7S III"])
    description: str = Field(examples=["Updated description"])
    type: str = Field(examples=["mirrorless"])


class RequisiteCreateRequest(BaseModel):
    title: str = Field(examples=["Vintage lamp"])
    description: str = Field(examples=["Warm decorative lamp"])
    type: str = Field(examples=["decor"])
    size: str = Field(examples=["m"])


class RequisiteUpdateRequest(BaseModel):
    title: str = Field(examples=["Vintage lamp"])
    description: str = Field(examples=["Updated description"])
    type: str = Field(examples=["decor"])
    size: str = Field(examples=["m"])


class ImageCreateRequest(BaseModel):
    file: str = Field(examples=["lamp.jpg"])
    title: str = Field(examples=["Lamp photo"])
    storage_key: str = Field(examples=["requisites/abcd1234.jpg"])
    bucket: str = Field(examples=["user"])
    mime_type: str = Field(examples=["image/jpeg"])
    size: int = Field(examples=[245678])
    description: str = Field(examples=["Front view"])


class BrokerUserRegistered(BaseModel):
    user_id: UUID = Field(examples=["0b8cf2c2-2a44-4fb8-aad8-9c37f2b6d8d4"])
    email: str = Field(examples=["user@example.com"])
    is_active: bool = Field(examples=[True])
    is_verified: bool = Field(examples=[True])
    is_superuser: bool = Field(examples=[False])
    create_at: datetime = Field(examples=["2026-01-10T09:30:00Z"])


class EquipmentListQuery(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=MAX_PAGE_SIZE)
    sort_by: Literal["create_at", "title", "type"] | None = None
    sort_dir: Literal["asc", "desc"] = "asc"
    type: str | None = None
    search: str | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None


class RequisiteListQuery(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=MAX_PAGE_SIZE)
    sort_by: Literal["create_at", "title", "type", "size"] | None = None
    sort_dir: Literal["asc", "desc"] = "asc"
    type: str | None = None
    size: str | None = None
    search: str | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None


class EquipmentItemResponse(BaseModel):
    oid: UUID
    user_id: UUID
    title: str
    description: str
    type: str
    create_at: datetime


class RequisiteItemResponse(EquipmentItemResponse):
    size: str


class EquipmentListResponse(BaseModel):
    items: list[EquipmentItemResponse]
    page: int
    page_size: int
    total_count: int
    pages: int


class RequisiteListResponse(BaseModel):
    items: list[RequisiteItemResponse]
    page: int
    page_size: int
    total_count: int
    pages: int
