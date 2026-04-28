from dataclasses import dataclass
from uuid import UUID

from app.application.ports.approvals import (
    ConfirmationTokenPort,
    ProjectMemberInvitationTokenData,
)
from app.application.ports.broker import EventPublisher
from app.domain.errors.confirmation import (
    ConfirmationTokenExpiredError,
    ConfirmationTokenInvalidError,
)


PROJECT_MEMBER_APPROVED_TOPIC = "project.member.approved"


@dataclass(frozen=True, slots=True)
class ProjectInvitationConfirmationResult:
    page: str
    title: str
    message: str


class ConfirmProjectInvitationByTokenHandler:
    def __init__(
        self,
        *,
        confirmation_tokens: ConfirmationTokenPort,
        publisher: EventPublisher,
    ) -> None:
        self._confirmation_tokens = confirmation_tokens
        self._publisher = publisher

    async def __call__(
        self,
        *,
        token: str,
        actor_user_id: UUID,
    ) -> ProjectInvitationConfirmationResult:
        try:
            payload = self._confirmation_tokens.decode_confirmation_token(token)
        except ConfirmationTokenExpiredError:
            return ProjectInvitationConfirmationResult(
                page="expired",
                title="Link expired",
                message="This project invitation link has expired.",
            )
        except ConfirmationTokenInvalidError:
            return _invalid_result()

        if not isinstance(payload, ProjectMemberInvitationTokenData):
            return _invalid_result()
        if payload.user_id != actor_user_id:
            return ProjectInvitationConfirmationResult(
                page="invalid",
                title="Wrong account",
                message="This project invitation belongs to another user.",
            )

        try:
            await self._publisher.publish(
                PROJECT_MEMBER_APPROVED_TOPIC,
                {
                    "project_id": str(payload.project_id),
                    "user_id": str(payload.user_id),
                    "approved_by_user_id": str(actor_user_id),
                },
            )
        except Exception:
            return ProjectInvitationConfirmationResult(
                page="error",
                title="Confirmation error",
                message="Could not accept the project invitation right now.",
            )

        return ProjectInvitationConfirmationResult(
            page="success",
            title="Project invitation accepted",
            message="The project invitation was accepted successfully.",
        )


def _invalid_result() -> ProjectInvitationConfirmationResult:
    return ProjectInvitationConfirmationResult(
        page="invalid",
        title="Invalid link",
        message="This project invitation link is invalid.",
    )
