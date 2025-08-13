from typing import Annotated
from pydantic import BaseModel, EmailStr, Field



class CreateUser(BaseModel):
    username: Annotated[
        str,
        Field(
            title="User Username",
            description="User username in system. Email must be unique in system.",
            examples=[
                "oleg4321dev",
            ],
        ),
    ]
    email: Annotated[
        EmailStr,
        Field(
            title="User Email",
            description="User email in system. Email must be unique in system.",
            examples=["user@gmail.com", "oleg4321@example.com"],
        ),
    ]
    password: Annotated[
        str,
        Field(
            min_length=4,
            max_length=24,
            title="User password",
            description="User password in system.",
            examples=["password", "paSsword412!qd"],
        ),
    ]


class ResponseUser(BaseModel):
    username: str
    email: str
    is_active: bool
    is_superuser: bool
    is_verified: bool


class TokenResponse(BaseModel):
    access_token: Annotated[str, Field(..., title="User Access Token.",
            description="User Access Token in system.",
            examples=['eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmN2UyN2YwNS1kMTNiLTRmYjItODE0ZC1jYWU4NWNjNDAwMjkiLCJpYXQiOjE3NTQ4NTM0MjksImV4cCI6MTc1NDg1NDAyOX0.Iy8-XKxu3-XzKus9QgJGaXHrhgd-y5YHoR-AO6wh_V1vp49RCXFIh_6Uq9TeTiHBqVnkUf9hKcoofsY8vjczO_vrlPrF7rAF-8jA0WlvVG-0qV5LylT89MIruR1wTl0pBVfWepmpiRivMuK95spfpkmzTPAxJZ4vUaRJRoAs0t7a1ZCwB2eCy6lrW_dFF4zkDfwOCoINhpKnocy0FVWR8wCVvF_Y2J7P_7XcTqALmXi_qqt8Cw834gjdfdhj7jJZ7YOTDrYXDtkxLB6olrY0mO_m9AMRd5Xh1j-e6fMq9s8K8EBo4kHI51maXzZcLEaKwY-SXtkS0pO16snFQGqGEw'],)]
    token_type: str = "Bearer"
