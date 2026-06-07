import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.application.errors.errors import InvalidCredentialsError
from app.application.use_case.authenticate_uc import JWTAuthServices
from app.infrastructure.errors.coder import NoValidTokenError
from app.infrastructure.security.jwt import JWTServices


def _build_jwt_services() -> JWTServices:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_pem = key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    config = SimpleNamespace(
        PRIVATE_KEY=private_pem,
        PUBLIC_KEY=public_pem,
        algoritm="RS256",
        access_token_time=600,
        refresh_token_time=3600,
    )
    return JWTServices(config)


class _FakeTx:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


class _FakeUsers:
    def __init__(self, user=None) -> None:
        self._user = user

    async def get(self, reference):
        if self._user is None or str(self._user.oid) != str(reference):
            return None
        return self._user


def _build_auth_service(jwt_services: JWTServices, user=None) -> JWTAuthServices:
    return JWTAuthServices(
        transaction_manager=_FakeTx(),
        password_hasher=SimpleNamespace(),
        jwt_coder=jwt_services,
        user_repository=_FakeUsers(user),
        generation=lambda: uuid4(),
    )


def test_decode_token_rejects_malformed_token() -> None:
    jwt_services = _build_jwt_services()
    with pytest.raises(NoValidTokenError):
        jwt_services.decode_token("not-a-jwt")


def test_decode_token_rejects_wrong_signature() -> None:
    signer = _build_jwt_services()
    verifier = _build_jwt_services()  # different keypair
    token = signer.create_refresh_token(str(uuid4()))
    with pytest.raises(NoValidTokenError):
        verifier.decode_token(token)


def test_refresh_with_garbage_token_raises_no_valid_token() -> None:
    service = _build_auth_service(_build_jwt_services())
    with pytest.raises(NoValidTokenError):
        asyncio.run(service.refresh_tokens("garbage.invalid.token"))


def test_refresh_with_access_token_is_rejected() -> None:
    jwt_services = _build_jwt_services()
    access_token = jwt_services.create_access_token(str(uuid4()), is_superuser=True)
    service = _build_auth_service(jwt_services)
    with pytest.raises(InvalidCredentialsError):
        asyncio.run(service.refresh_tokens(access_token))


def test_refresh_for_missing_user_is_rejected() -> None:
    jwt_services = _build_jwt_services()
    refresh_token = jwt_services.create_refresh_token(str(uuid4()))
    service = _build_auth_service(jwt_services, user=None)
    with pytest.raises(InvalidCredentialsError):
        asyncio.run(service.refresh_tokens(refresh_token))


def test_refresh_for_existing_user_issues_new_tokens() -> None:
    jwt_services = _build_jwt_services()
    user_id = uuid4()
    user = SimpleNamespace(oid=user_id, is_superuser=False)
    refresh_token = jwt_services.create_refresh_token(str(user_id))
    service = _build_auth_service(jwt_services, user=user)

    tokens = asyncio.run(service.refresh_tokens(refresh_token))

    assert tokens["access_token"]
    assert tokens["refresh_token"]
    access_payload = jwt_services.decode_token(tokens["access_token"])
    assert access_payload["sub"] == str(user_id)
    assert access_payload["type"] == "access"
    assert access_payload["is_superuser"] is False
    refresh_payload = jwt_services.decode_token(tokens["refresh_token"])
    assert refresh_payload["type"] == "refresh"
