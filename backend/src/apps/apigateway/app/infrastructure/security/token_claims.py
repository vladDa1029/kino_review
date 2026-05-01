from typing import Literal, NotRequired, TypedDict


class BaseTokenClaims(TypedDict):
    sub: str
    type: Literal["access", "refresh"]
    iat: int
    exp: int


class AccessTokenClaims(BaseTokenClaims):
    type: Literal["access"]
    is_superuser: NotRequired[bool]


class RefreshTokenClaims(BaseTokenClaims):
    type: Literal["refresh"]
    jti: str
