import uuid
from pydantic import UUID4, BaseModel, EmailStr, Field

from app.domain.entities import User


class CreateUser(BaseModel):
    username: str = Field(min_length=3, max_length=125)
    email: EmailStr
    password: str

    def from_entities(self) -> User:
        return User(
            username=self.username,
            oid=uuid.uuid4(),
            email=str(self.email),
            password=self.password,
        )


class ResponseUser(BaseModel):
    username: str
    email: str
    is_active: bool
    is_superuser: bool
    is_verified: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
