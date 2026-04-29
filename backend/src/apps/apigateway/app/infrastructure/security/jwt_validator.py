from typing import Any
import jwt


class JWTValidationError(Exception):
    pass


class JWTValidator:
    def __init__(self, public_key: bytes, algorithm: str) -> None:
        self._public_key = public_key
        self._algorithm = algorithm

    def decode(self, token: str) -> dict[str, Any]:
        try:
            return jwt.decode(
                jwt=token,
                key=self._public_key,
                algorithms=[self._algorithm],
            )
        except jwt.PyJWTError as exc:
            raise JWTValidationError("Invalid token") from exc
