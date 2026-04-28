from dataclasses import dataclass

from app.application.ports.email import EmailMessage, EmailSender


@dataclass(frozen=True, slots=True, kw_only=True)
class SendNotificationEmailCommand:
    recipient_email: str
    subject: str
    template: str
    payload: dict[str, str | None]


class SendNotificationEmailHandler:
    def __init__(self, *, sender: EmailSender) -> None:
        self._sender = sender

    async def __call__(self, command: SendNotificationEmailCommand) -> None:
        await self._sender.send(
            EmailMessage(
                recipient_email=command.recipient_email,
                subject=command.subject,
                body=_render_email(command.template, command.payload),
            )
        )


def _render_email(template: str, payload: dict[str, str | None]) -> str:
    if template == "project_member_invitation":
        return _render_project_member_invitation(payload)
    if template != "reservation_confirmation":
        raise ValueError(f"Unsupported email template: {template}")

    confirm_url = payload.get("confirm_url") or ""
    project_title = payload.get("project_title") or "Untitled project"
    shift_title = payload.get("shift_title") or "Untitled shift"
    time_from = payload.get("time_from") or ""
    time_to = payload.get("time_to") or ""
    role = payload.get("role")
    resource_type = payload.get("resource_type")

    subject_line = f"Project: {project_title}"
    details = f"Shift: {shift_title}\nTime: {time_from} -> {time_to}"
    if role:
        details += f"\nRole: {role}"
    if resource_type:
        details += f"\nResource type: {resource_type}"

    return (
        f"{subject_line}\n"
        f"{details}\n\n"
        "Open the link below to confirm the reservation:\n"
        f"{confirm_url}\n"
    )


def _render_project_member_invitation(payload: dict[str, str | None]) -> str:
    accept_url = payload.get("accept_url") or ""
    project_title = payload.get("project_title") or "Untitled project"
    role = payload.get("role") or "member"

    return (
        f"Project: {project_title}\n"
        f"Role: {role}\n\n"
        "Open the link below while signed in to accept the project invitation:\n"
        f"{accept_url}\n"
    )
