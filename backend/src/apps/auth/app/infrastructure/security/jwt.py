from dataclasses import dataclass, field
import datetime
from typing import Any, Dict, Literal, Optional, Set
from uuid import uuid4
import uuid
from app.config import Auth
import structlog
import jwt

from app.infrastructure.errors.coder import NoValidTokenError

log = structlog.get_logger(__file__)


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

    def __str__(self) -> str:
        return str(self.jti)


class JWTServices:
    """Class for encoding and decoding jwt"""

    def __init__(self, config: Auth):
        self._config = config

    def _create_token(
        self,
        sub: str,
        time: int,
        type: Literal["access", "refresh"] = "access",
        include: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a token by user ID."""
        if type == "refresh":
            payload = TokenPayload(sub, time, type=type).to_dict(
                include={"jti": str(RefreshTokenJti())}
            )
            log.debug(f"{payload=}")

            return jwt.encode(
                payload=payload,
                key=self._config.PRIVATE_KEY,
                algorithm=self._config.algoritm,
            )
        payload = TokenPayload(sub, time, type=type).to_dict(include=include)
        return jwt.encode(
            payload=payload,
            key=self._config.PRIVATE_KEY,
            algorithm=self._config.algoritm,
        )

    def create_access_token(
        self,
        sub: str,
        is_superuser: bool | None = None,
    ) -> str:
        extra_claims: Dict[str, Any] = {}
        if is_superuser is not None:
            extra_claims["is_superuser"] = is_superuser
        include = extra_claims if extra_claims else None
        return self._create_token(
            sub=sub,
            time=self._config.access_token_time,
            include=include,
        )

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
            log.info(ex)
            raise NoValidTokenError()
        return payload
