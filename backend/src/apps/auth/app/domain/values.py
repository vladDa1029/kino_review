from dataclasses import dataclass, field
import datetime
from enum import Enum
from typing import Any, Dict, Optional, Set
from uuid import uuid4
import uuid


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


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
