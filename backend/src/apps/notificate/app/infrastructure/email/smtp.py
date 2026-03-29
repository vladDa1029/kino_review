import asyncio
import smtplib
from email.message import EmailMessage as MIMEEmailMessage

from app.application.ports.email import EmailMessage, EmailSender
from app.config import SMTP


class SMTPEmailSender(EmailSender):
    def __init__(self, settings: SMTP) -> None:
        self._settings = settings

    async def send(self, message: EmailMessage) -> None:
        await asyncio.to_thread(self._send_blocking, message)

    def _send_blocking(self, message: EmailMessage) -> None:
        mime = MIMEEmailMessage()
        mime["From"] = _format_from(self._settings)
        mime["To"] = message.recipient_email
        mime["Subject"] = message.subject
        mime.set_content(message.body)

        if self._settings.use_tls:
            with smtplib.SMTP_SSL(
                host=self._settings.host,
                port=self._settings.port,
                timeout=self._settings.timeout_seconds,
            ) as smtp:
                self._login_if_needed(smtp)
                smtp.send_message(mime)
            return

        with smtplib.SMTP(
            host=self._settings.host,
            port=self._settings.port,
            timeout=self._settings.timeout_seconds,
        ) as smtp:
            if self._settings.starttls:
                smtp.starttls()
            self._login_if_needed(smtp)
            smtp.send_message(mime)

    def _login_if_needed(self, smtp: smtplib.SMTP) -> None:
        if self._settings.username and self._settings.password:
            smtp.login(self._settings.username, self._settings.password)


def _format_from(settings: SMTP) -> str:
    if settings.from_name:
        return f"{settings.from_name} <{settings.from_email}>"
    return settings.from_email
