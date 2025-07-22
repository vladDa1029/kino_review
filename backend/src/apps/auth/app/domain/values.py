from ast import Set
from dataclasses import dataclass, field
import datetime
from enum import Enum
from typing import Any, Dict, Optional


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
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).timestamp()
    )
    exp: int = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "exp",
            (
                datetime.datetime.now(datetime.timezone.utc)
                + datetime.timedelta(seconds=self.add_exp)
            ).timestamp(),
        )

    def is_expired(self) -> bool:
        """Check if token has expired."""
        return self.exp < self.iat

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
