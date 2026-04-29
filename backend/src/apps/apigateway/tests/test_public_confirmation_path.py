from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.presentation.middleware.auth import AuthGatewayMiddleware


class DummySettings:
    token_type_claim = "type"
    user_id_claim = "sub"


class RejectingValidator:
    def decode(self, token: str):
        raise AssertionError("validator should not be called for public path")


class AcceptingValidator:
    def decode(self, token: str):
        return {"sub": "user-123", "type": "access"}


def test_public_confirmation_path_bypasses_auth() -> None:
    app = FastAPI()

    @app.get("/user/confirmations/test-token")
    async def confirmation() -> dict[str, str]:
        return {"status": "ok"}

    app.add_middleware(
        AuthGatewayMiddleware,
        settings=DummySettings(),
        validator=RejectingValidator(),
        protected_paths=["/user*"],
        public_paths=["/user/confirmations/*"],
    )

    client = TestClient(app)

    response = client.get("/user/confirmations/test-token")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_project_invitation_path_requires_auth() -> None:
    app = FastAPI()

    @app.get("/user/project-invitations/test-token")
    async def project_invitation() -> dict[str, str]:
        return {"status": "ok"}

    app.add_middleware(
        AuthGatewayMiddleware,
        settings=DummySettings(),
        validator=RejectingValidator(),
        protected_paths=["/user*"],
        public_paths=["/user/confirmations/*"],
    )

    client = TestClient(app)

    response = client.get("/user/project-invitations/test-token")

    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


def test_project_invitation_path_sets_trusted_user_headers_when_authenticated() -> None:
    app = FastAPI()

    @app.get("/user/project-invitations/test-token")
    async def project_invitation(request: Request) -> dict[str, str]:
        return request.state.user_headers

    app.add_middleware(
        AuthGatewayMiddleware,
        settings=DummySettings(),
        validator=AcceptingValidator(),
        protected_paths=["/user*"],
        public_paths=["/user/confirmations/*"],
    )

    client = TestClient(app)

    response = client.get(
        "/user/project-invitations/test-token",
        headers={"Authorization": "Bearer access-token"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "x-user-id": "user-123",
        "x-user-token-type": "access",
    }
