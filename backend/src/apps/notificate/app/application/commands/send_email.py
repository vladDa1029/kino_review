from dataclasses import dataclass

from app.application.commands.email_templates import render_email_html
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
                html_body=render_email_html(command.template, command.payload),
            )
        )


def _render_email(template: str, payload: dict[str, str | None]) -> str:
    if template == "project_member_invitation":
        return _render_project_member_invitation(payload)
    if template == "shift_reminder":
        return _render_shift_reminder(payload)
    if template != "reservation_confirmation":
        raise ValueError(f"Unsupported email template: {template}")

    confirm_url = payload.get("confirm_url") or ""
    project_title = payload.get("project_title") or "Без названия"
    shift_title = payload.get("shift_title") or "Без названия"
    time_from = payload.get("time_from") or ""
    time_to = payload.get("time_to") or ""
    role = payload.get("role")
    resource_type = payload.get("resource_type")

    details = f"Проект: {project_title}\nСмена: {shift_title}\nВремя: {time_from} -> {time_to}"
    if role:
        details += f"\nРоль: {role}"
    if resource_type:
        details += f"\nТип ресурса: {resource_type}"

    return (
        "Подтвердите участие в смене.\n\n"
        f"{details}\n\n"
        "Откройте ссылку ниже, чтобы подтвердить участие:\n"
        f"{confirm_url}\n"
    )


def _render_shift_reminder(payload: dict[str, str | None]) -> str:
    shift_url = payload.get("shift_url") or ""
    project_title = payload.get("project_title") or "Без названия"
    shift_title = payload.get("shift_title") or "Без названия"
    time_from = payload.get("time_from") or ""
    time_to = payload.get("time_to") or ""
    role = payload.get("role")
    resources = payload.get("resources")

    details = (
        f"Проект: {project_title}\n"
        f"Смена: {shift_title}\n"
        f"Время: {time_from} -> {time_to}"
    )
    if role:
        details += f"\nРоль: {role}"

    resources_block = (
        f"\n\nВзять с собой:\n{resources}"
        if resources
        else "\n\nНичего приносить не нужно."
    )

    return (
        "Ваша смена скоро начнётся.\n"
        f"{details}"
        f"{resources_block}\n\n"
        "Подробности смены:\n"
        f"{shift_url}\n"
    )


def _render_project_member_invitation(payload: dict[str, str | None]) -> str:
    accept_url = payload.get("accept_url") or ""
    project_title = payload.get("project_title") or "Без названия"
    role = payload.get("role") or "участник"

    return (
        f"Проект: {project_title}\n"
        f"Роль: {role}\n\n"
        "Войдите в аккаунт и откройте ссылку ниже, чтобы принять приглашение:\n"
        f"{accept_url}\n"
    )
