from uuid import uuid4

from app.application.ports.broker import EventPublisher
from app.application.ports.reporting import (
    ShiftReportParticipantContext,
    ShiftReportResourceContext,
    ShiftReportResourceDetails,
    ShiftReportSnapshot,
    ShiftReportSnapshotPort,
    ShiftReportUserDetails,
)
from app.config import UserService
from app.domain.errors.business import ExternalServiceError
from app.infrastructure.broker.request_reply import BrokerReplyInbox
from app.presentation.schemas import BrokerShiftReportSnapshotReply

SHIFT_REPORT_SNAPSHOT_REQUESTED_TOPIC = "shift.report_snapshot_requested"
SHIFT_REPORT_SNAPSHOT_PROVIDED = "shift.report_snapshot_provided"
SHIFT_REPORT_SNAPSHOT_FAILED = "shift.report_snapshot_failed"


class ShiftReportSnapshotBrokerClient(ShiftReportSnapshotPort):
    def __init__(
        self,
        *,
        settings: UserService,
        publisher: EventPublisher,
        reply_inbox: BrokerReplyInbox,
    ) -> None:
        self._settings = settings
        self._publisher = publisher
        self._reply_inbox = reply_inbox

    async def fetch_snapshot(
        self,
        *,
        report_id,
        project_id,
        shift_id,
        participants: tuple[ShiftReportParticipantContext, ...],
        resources: tuple[ShiftReportResourceContext, ...],
    ) -> ShiftReportSnapshot:
        correlation_id = str(uuid4())
        self._reply_inbox.register(correlation_id)
        try:
            await self._publisher.publish(
                SHIFT_REPORT_SNAPSHOT_REQUESTED_TOPIC,
                {
                    "correlation_id": correlation_id,
                    "reply_topic": self._reply_inbox.reply_topic,
                    "report_id": str(report_id),
                    "project_id": str(project_id),
                    "shift_id": str(shift_id),
                    "participants": [
                        {
                            "participant_id": str(item.participant_id),
                            "user_id": str(item.user_id),
                            "project_role": item.project_role,
                            "shift_role": item.shift_role,
                            "time_from": item.time_from.isoformat(),
                            "time_to": item.time_to.isoformat(),
                        }
                        for item in participants
                    ],
                    "resources": [
                        {
                            "resource_request_id": str(item.resource_request_id),
                            "resource_id": str(item.resource_id),
                            "owner_user_id": str(item.owner_user_id),
                            "resource_type": item.resource_type,
                            "time_from": item.time_from.isoformat(),
                            "time_to": item.time_to.isoformat(),
                        }
                        for item in resources
                    ],
                },
            )
        except Exception as exc:
            self._reply_inbox.discard(correlation_id)
            raise ExternalServiceError(f"Report snapshot publish failed: {exc}") from exc

        try:
            payload = await self._reply_inbox.wait_for(
                correlation_id,
                timeout=self._settings.timeout_seconds,
            )
        except TimeoutError as exc:
            raise ExternalServiceError("Report snapshot reply timed out.") from exc

        try:
            reply = BrokerShiftReportSnapshotReply.model_validate(payload)
        except Exception as exc:
            raise ExternalServiceError("Report snapshot reply payload is invalid.") from exc

        if str(reply.correlation_id) != correlation_id:
            raise ExternalServiceError("Report snapshot reply correlation mismatch.")
        if reply.response_type == SHIFT_REPORT_SNAPSHOT_FAILED:
            raise ExternalServiceError(reply.reason or "User-service report snapshot failed.")

        return ShiftReportSnapshot(
            users=tuple(
                ShiftReportUserDetails(
                    user_id=item.user_id,
                    username=item.username,
                    phone=item.phone,
                    email=item.email,
                )
                for item in reply.users
            ),
            resources=tuple(
                ShiftReportResourceDetails(
                    resource_id=item.resource_id,
                    owner_user_id=item.owner_user_id,
                    title=item.title,
                    resource_type=item.resource_type,
                    description=item.description,
                    size=item.size,
                )
                for item in reply.resources
            ),
        )
