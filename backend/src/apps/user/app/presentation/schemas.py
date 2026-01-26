from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


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
