from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from app.application.ports.approvals import (
    ConfirmationTokenPort,
    ParticipantConfirmationTokenData,
    ResourceConfirmationTokenData,
)
from app.config import ConfirmationSettings
from app.domain.errors.confirmation import (
    ConfirmationTokenExpiredError,
    ConfirmationTokenInvalidError,
)


class JWTConfirmationTokenService(ConfirmationTokenPort):
    def __init__(self, settings: ConfirmationSettings) -> None:
        self._settings = settings

    def issue_participant_token(
        self,
        *,
        request_id,
        project_id,
        shift_id,
        participant_id,
        user_id,
        time_from,
        time_to,
    ) -> str:
        return self._encode(
            {
                "type": "participant_approval",
                "request_id": str(request_id),
                "project_id": str(project_id),
                "shift_id": str(shift_id),
                "participant_id": str(participant_id),
                "user_id": str(user_id),
                "time_from": time_from.isoformat(),
                "time_to": time_to.isoformat(),
            }
        )

    def issue_resource_token(
        self,
        *,
        request_id,
        project_id,
        shift_id,
        resource_request_id,
        owner_user_id,
        resource_id,
        time_from,
        time_to,
    ) -> str:
        return self._encode(
            {
                "type": "resource_request_approval",
                "request_id": str(request_id),
                "project_id": str(project_id),
                "shift_id": str(shift_id),
                "resource_request_id": str(resource_request_id),
                "owner_user_id": str(owner_user_id),
                "resource_id": str(resource_id),
                "time_from": time_from.isoformat(),
                "time_to": time_to.isoformat(),
            }
        )

    def decode_confirmation_token(
        self,
        token: str,
    ) -> ParticipantConfirmationTokenData | ResourceConfirmationTokenData:
        try:
            payload = jwt.decode(
                jwt=token,
                key=self._settings.secret_key,
                algorithms=[self._settings.algorithm],
            )
        except jwt.ExpiredSignatureError as exc:
            raise ConfirmationTokenExpiredError() from exc
        except jwt.PyJWTError as exc:
            raise ConfirmationTokenInvalidError() from exc

        token_type = payload.get("type")
        try:
            if token_type == "participant_approval":
                return ParticipantConfirmationTokenData(
                    request_id=UUID(payload["request_id"]),
                    project_id=UUID(payload["project_id"]),
                    shift_id=UUID(payload["shift_id"]),
                    participant_id=UUID(payload["participant_id"]),
                    user_id=UUID(payload["user_id"]),
                    time_from=datetime.fromisoformat(payload["time_from"]),
                    time_to=datetime.fromisoformat(payload["time_to"]),
                )
            if token_type == "resource_request_approval":
                return ResourceConfirmationTokenData(
                    request_id=UUID(payload["request_id"]),
                    project_id=UUID(payload["project_id"]),
                    shift_id=UUID(payload["shift_id"]),
                    resource_request_id=UUID(payload["resource_request_id"]),
                    owner_user_id=UUID(payload["owner_user_id"]),
                    resource_id=UUID(payload["resource_id"]),
                    time_from=datetime.fromisoformat(payload["time_from"]),
                    time_to=datetime.fromisoformat(payload["time_to"]),
                )
        except (KeyError, TypeError, ValueError) as exc:
            raise ConfirmationTokenInvalidError() from exc

        raise ConfirmationTokenInvalidError()

    def _encode(self, payload: dict[str, str]) -> str:
        now = datetime.now(tz=UTC)
        exp = now + timedelta(hours=self._settings.ttl_hours)
        return jwt.encode(
            payload={
                **payload,
                "iat": int(now.timestamp()),
                "exp": int(exp.timestamp()),
            },
            key=self._settings.secret_key,
            algorithm=self._settings.algorithm,
        )
