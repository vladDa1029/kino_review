from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.application.common.pagination import MAX_PAGE_SIZE


class DescriptionCreateRequest(BaseModel):
    username: str
    phone: str


class DescriptionUpdateRequest(BaseModel):
    username: str
    phone: str


class SpareTimeCreateRequest(BaseModel):
    start_time: datetime
    end_time: datetime


class ReserveAvailabilityRequest(BaseModel):
    owner_id: UUID
    obj_id: UUID
    start_time: datetime
    end_time: datetime


class EquipmentCreateRequest(BaseModel):
    title: str
    description: str
    type: str


class EquipmentUpdateRequest(BaseModel):
    title: str
    description: str
    type: str


class RequisiteCreateRequest(BaseModel):
    title: str
    description: str
    type: str
    size: str


class RequisiteUpdateRequest(BaseModel):
    title: str
    description: str
    type: str
    size: str


class ImageCreateRequest(BaseModel):
    file: str
    title: str
    storage_key: str
    bucket: str
    mime_type: str
    size: int
    description: str


class BrokerUserRegistered(BaseModel):
    user_id: UUID
    email: str
    is_active: bool
    is_verified: bool
    is_superuser: bool
    create_at: datetime


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
