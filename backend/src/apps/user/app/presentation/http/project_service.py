from uuid import UUID, uuid4

from app.application.ports.approvals import (
    ParticipantApprovalState,
    ProjectApprovalStatePort,
    ResourceApprovalState,
)
from app.application.ports.broker import EventPublisher
from app.config import ProjectService
from app.domain.errors.base import ApplicationError
from app.infrastructure.adapters.request_reply import BrokerReplyInbox
from app.presentation.schemas import (
    BrokerShiftParticipantApprovalStateReply,
    BrokerShiftResourceRequestApprovalStateReply,
)

PARTICIPANT_APPROVAL_STATE_REQUESTED_TOPIC = "shift.participant_approval_state_requested"
RESOURCE_APPROVAL_STATE_REQUESTED_TOPIC = "shift.resource_request_approval_state_requested"
PARTICIPANT_APPROVAL_STATE_PROVIDED = "shift.participant_approval_state_provided"
PARTICIPANT_APPROVAL_STATE_FAILED = "shift.participant_approval_state_failed"
RESOURCE_APPROVAL_STATE_PROVIDED = "shift.resource_request_approval_state_provided"
RESOURCE_APPROVAL_STATE_FAILED = "shift.resource_request_approval_state_failed"


class ProjectApprovalStateError(ApplicationError):
    """Project approval state is unavailable."""


class ProjectApprovalStateBrokerClient(ProjectApprovalStatePort):
    def __init__(
        self,
        settings: ProjectService,
        publisher: EventPublisher,
        reply_inbox: BrokerReplyInbox,
    ) -> None:
        self._settings = settings
        self._publisher = publisher
        self._reply_inbox = reply_inbox

    async def get_participant_approval_state(
        self,
        *,
        participant_id: UUID,
    ) -> ParticipantApprovalState:
        payload = await self._request(
            topic=PARTICIPANT_APPROVAL_STATE_REQUESTED_TOPIC,
            request_payload={
                "participant_id": str(participant_id),
            },
        )
        try:
            event = BrokerShiftParticipantApprovalStateReply.model_validate(payload)
        except Exception as exc:
            raise ProjectApprovalStateError("Project-service returned invalid approval-state payload.") from exc

        if event.response_type == PARTICIPANT_APPROVAL_STATE_FAILED:
            raise ProjectApprovalStateError(event.reason or "Approval request was not found in project-service.")

        return ParticipantApprovalState(
            request_id=_require(event.request_id, "request_id"),
            project_id=_require(event.project_id, "project_id"),
            project_title=_require(event.project_title, "project_title"),
            shift_id=_require(event.shift_id, "shift_id"),
            shift_title=_require(event.shift_title, "shift_title"),
            participant_id=_require(event.participant_id, "participant_id"),
            user_id=_require(event.user_id, "user_id"),
            role=_require(event.role, "role"),
            time_from=_require(event.time_from, "time_from"),
            time_to=_require(event.time_to, "time_to"),
            status=_require(event.status, "status"),
            status_name=_require(event.status_name, "status_name"),
            user_reservation_id=event.user_reservation_id,
            reserve_failure_reason=event.reserve_failure_reason,
        )

    async def get_resource_approval_state(
        self,
        *,
        resource_request_id: UUID,
    ) -> ResourceApprovalState:
        payload = await self._request(
            topic=RESOURCE_APPROVAL_STATE_REQUESTED_TOPIC,
            request_payload={
                "resource_request_id": str(resource_request_id),
            },
        )
        try:
            event = BrokerShiftResourceRequestApprovalStateReply.model_validate(payload)
        except Exception as exc:
            raise ProjectApprovalStateError("Project-service returned invalid approval-state payload.") from exc

        if event.response_type == RESOURCE_APPROVAL_STATE_FAILED:
            raise ProjectApprovalStateError(event.reason or "Approval request was not found in project-service.")

        return ResourceApprovalState(
            request_id=_require(event.request_id, "request_id"),
            project_id=_require(event.project_id, "project_id"),
            project_title=_require(event.project_title, "project_title"),
            shift_id=_require(event.shift_id, "shift_id"),
            shift_title=_require(event.shift_title, "shift_title"),
            resource_request_id=_require(event.resource_request_id, "resource_request_id"),
            owner_user_id=_require(event.owner_user_id, "owner_user_id"),
            resource_id=_require(event.resource_id, "resource_id"),
            resource_type=_require(event.resource_type, "resource_type"),
            time_from=_require(event.time_from, "time_from"),
            time_to=_require(event.time_to, "time_to"),
            status=_require(event.status, "status"),
            status_name=_require(event.status_name, "status_name"),
            resource_reservation_id=event.resource_reservation_id,
            reserve_failure_reason=event.reserve_failure_reason,
        )

    async def _request(
        self,
        *,
        topic: str,
        request_payload: dict[str, str],
    ) -> dict:
        correlation_id = str(uuid4())
        self._reply_inbox.register(correlation_id)
        try:
            await self._publisher.publish(
                topic,
                {
                    "correlation_id": correlation_id,
                    "reply_topic": self._reply_inbox.reply_topic,
                    **request_payload,
                },
            )
        except Exception as exc:
            self._reply_inbox.discard(correlation_id)
            raise ProjectApprovalStateError(f"Project-service request publish failed: {exc}") from exc

        try:
            payload = await self._reply_inbox.wait_for(
                correlation_id,
                timeout=self._settings.timeout_seconds,
            )
        except TimeoutError as exc:
            raise ProjectApprovalStateError("Project-service approval-state reply timed out.") from exc

        if str(payload.get("correlation_id")) != correlation_id:
            raise ProjectApprovalStateError("Project-service returned mismatched correlation id.")
        return payload


def _require(value, field_name: str):
    if value is None:
        raise ProjectApprovalStateError(
            f"Project-service returned invalid approval-state payload: missing {field_name}."
        )
    return value
