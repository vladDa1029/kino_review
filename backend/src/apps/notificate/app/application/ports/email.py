from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class EmailMessage:
    recipient_email: str
    subject: str
    body: str
    html_body: str | None = None


class EmailSender(Protocol):
    async def send(self, message: EmailMessage) -> None:
        raise NotImplementedError
