from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str


class ReservationConfirmationPayload(BaseModel):
    confirm_url: str
    project_title: str
    shift_title: str
    time_from: str
    time_to: str
    role: str | None = None
    resource_type: str | None = None


class ProjectMemberInvitationPayload(BaseModel):
    accept_url: str
    project_title: str
    role: str
    invited_by_user_id: str | None = None


class BrokerNotificationEmailRequested(BaseModel):
    notification_id: str
    recipient_email: str
    subject: str
    template: str
    payload: ReservationConfirmationPayload | ProjectMemberInvitationPayload
