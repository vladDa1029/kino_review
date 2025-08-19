from dataclasses import dataclass, field
import datetime
from typing import Any, Dict, Literal, Optional, Set
from uuid import uuid4
import uuid
from app.config import Auth

import jwt

from app.infrastructure.exceptions.coder import NoValidTokenExption


@dataclass(frozen=True)
class TokenPayload:
    """
    Payloads token(JSON Web Token).

    TODO: Дописать доку.

    Parameters:
    - sub (str): Users identificate.
    - add_exp (int): How many time lives for token in seconds (exp).

    """

    sub: str = field()
    add_exp: int = field()
    type: Literal["access", "refresh"] = field(default="access")
    iat: int = field(
        default_factory=lambda: int(
            datetime.datetime.now(datetime.timezone.utc).timestamp()
        )
    )
    exp: int = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "exp",
            int(
                (
                    datetime.datetime.now(datetime.timezone.utc)
                    + datetime.timedelta(seconds=self.add_exp)
                ).timestamp()
            ),
        )

    def is_expired(self) -> bool:
        """Check if token has expired."""
        return self.exp < int(datetime.datetime.now(datetime.timezone.utc).timestamp())

    def to_dict(
        self,
        include: Optional[Dict[str, Any]] = None,
        exclude: Optional[Set] = None,
    ) -> Dict[str, Any]:
        """Convert to dictionary with field filtring"""

        data: Dict[str, Any] = vars(self).copy()

        data.pop("add_exp", None)

        if include:
            data.update(include)

        if exclude:
            for key in exclude:
                data.pop(key, None)

        return data


@dataclass(frozen=True)
class RefreshTokenJti:
    jti: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self):
        try:
            uuid.UUID(self.jti, version=4)
        except ValueError:
            raise ValueError("Invalid UUID format")


class JWTServices:
    """Class for encoding and decoding jwt"""

    def __init__(self, config: Auth):
        self._config = config

    def _create_token(
        self, sub: str, time: int, type: Literal["access", "refresh"] = "access"
    ) -> str:
        """Create a token by user ID."""
        return jwt.encode(
            payload=TokenPayload(sub, time, type=type).to_dict(),
            key=self._config.PRIVATE_KEY,
            algorithm=self._config.algoritm,
        )

    def create_access_token(self, sub: str) -> str:
        return self._create_token(sub=sub, time=self._config.access_token_time)

    def create_refresh_token(self, sub) -> str:
        return self._create_token(sub, self._config.refresh_token_time, type="refresh")

    def decode_token(self, encode_token: str) -> dict[str, Any]:
        """Decoded token"""
        try:
            payload = jwt.decode(
                jwt=encode_token,
                key=self._config.PUBLIC_KEY,
                algorithms=[self._config.algoritm],
            )
        except (jwt.ExpiredSignatureError, jwt.InvalidSignatureError) as ex:
            raise NoValidTokenExption(ex=ex)
        return payload
