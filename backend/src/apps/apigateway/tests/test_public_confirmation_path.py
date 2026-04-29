from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.presentation.middleware.auth import AuthGatewayMiddleware


class DummySettings:
    token_type_claim = "type"
    user_id_claim = "sub"


class DummyValidator:
    def decode(self, token: str):
        raise AssertionError("validator should not be called for public path")


def test_public_confirmation_path_bypasses_auth() -> None:
    app = FastAPI()

    @app.get("/user/confirmations/test-token")
    async def confirmation() -> dict[str, str]:
        return {"status": "ok"}

    app.add_middleware(
        AuthGatewayMiddleware,
        settings=DummySettings(),
        validator=DummyValidator(),
        protected_paths=["/user*"],
        public_paths=["/user/confirmations/*"],
    )

    client = TestClient(app)

    response = client.get("/user/confirmations/test-token")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
