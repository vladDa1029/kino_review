import uuid
from pydantic import BaseModel, EmailStr

from app.domain.entities import User


class CreateUsers(BaseModel):
    email: EmailStr
    password: str

    def from_entities(self) -> User:
        return User(
            oid=uuid.uuid4(),
            email=str(self.email),
            password=self.password,
        )


class ResponseUsers(BaseModel):
    email: str
    password: str
    is_active: bool
    is_superuser: bool
    is_verified: bool
