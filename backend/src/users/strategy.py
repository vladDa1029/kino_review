from fastapi_users.authentication import AuthenticationBackend
from src.settings.config import get_settings

from .transport import bearer_transport
from fastapi_users.authentication import JWTStrategy

settings = get_settings()


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(
        secret=settings.auth.PRIVATE_KEY,  # private key
        lifetime_seconds=settings.auth.access_token_time,
        algorithm=settings.auth.algoritm,
        public_key=settings.auth.PUBLIC_KEY,
    )


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)
