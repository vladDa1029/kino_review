from dataclasses import asdict
from typing import Any
from app.config import get_settings
from app.domain import values
import jwt

settings = get_settings()


class JWT:

    def create_token(self, sub: str, time: int) -> str:
        """Create a token by user ID."""
        return jwt.encode(
            payload=values.TokenPayload(sub, settings.auth.access_token_time).to_dict(),
            key=settings.auth.PRIVATE_KEY,
            algorithm=settings.auth.algoritm,
        )

    def decode_token(self, encode_token: str)-> dict[str, Any]:
        """Decoded token"""
        payload = jwt.decode(
            jwt=encode_token,
            key=settings.auth.PUBLIC_KEY,
            algorithms=[settings.auth.algoritm],
        )
        return payload
