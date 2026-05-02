from typing import Any

import jwt
import structlog

from .token_claims import AccessTokenClaims

log =structlog.get_logger(__file__)

class JWTValidationError(Exception):
    pass


class JWTValidator:
    def __init__(self, public_key: bytes, algorithm: str) -> None:
        self._public_key = public_key
        self._algorithm = algorithm

    def decode(self, token: str) -> AccessTokenClaims[str, Any]:
        try:
            data =AccessTokenClaims(
                jwt.decode(
                    jwt=token,
                    key=self._public_key,
                    algorithms=[self._algorithm],
                )
            )
            log.debug("Token : ", data)
            return data
        except jwt.PyJWTError as exc:
            raise JWTValidationError("Invalid token") from exc
