import asyncio

import pytest

from app.application.commands.email_templates import ACCENT, render_email_html
from app.application.commands.schedule_notifications import (
    ScheduleNotificationEmailCommand,
    ScheduleNotificationEmailHandler,
)
from app.application.commands.send_email import (
    SendNotificationEmailCommand,
    SendNotificationEmailHandler,
)
from app.config import TaskIQ
from app.infrastructure.taskiq.broker import create_taskiq_broker
from app.infrastructure.taskiq.dispatcher import TaskiqNotificationTaskDispatcher


class FakeDispatcher:
    def __init__(self) -> None:
        self.commands: list[ScheduleNotificationEmailCommand] = []

    async def schedule_email(
        self,
        command: ScheduleNotificationEmailCommand,
    ) -> None:
        self.commands.append(command)


class FakeSender:
    def __init__(self) -> None:
        self.messages = []

    async def send(self, message) -> None:
        self.messages.append(message)


class FakeTask:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def kiq(self, **kwargs) -> None:
        self.calls.append(kwargs)


class FakeBroker:
    def __init__(self, task: FakeTask | None) -> None:
        self._task = task

    def find_task(self, task_name: str):
        assert task_name == "notificate.send_notification_email"
        return self._task


def test_schedule_email_dispatches_task() -> None:
    async def scenario() -> None:
        dispatcher = FakeDispatcher()
        handler = ScheduleNotificationEmailHandler(dispatcher=dispatcher)
        command = ScheduleNotificationEmailCommand(
            notification_id="notif-1",
            recipient_email="user@example.com",
            subject="Confirm reservation",
            template="reservation_confirmation",
            payload={
                "confirm_url": "http://localhost:8000/user/confirmations/token",
                "project_title": "Feature film",
                "shift_title": "Night shoot",
                "time_from": "2026-01-10T10:00:00+00:00",
                "time_to": "2026-01-10T11:00:00+00:00",
                "role": "ACTOR",
                "resource_type": None,
            },
        )

        await handler(command)

        assert dispatcher.commands == [command]

    asyncio.run(scenario())


def test_send_email_renders_reservation_confirmation_body() -> None:
    async def scenario() -> None:
        sender = FakeSender()
        handler = SendNotificationEmailHandler(sender=sender)
        command = SendNotificationEmailCommand(
            recipient_email="user@example.com",
            subject="Confirm reservation",
            template="reservation_confirmation",
            payload={
                "confirm_url": "http://localhost:8000/user/confirmations/token",
                "project_title": "Feature film",
                "shift_title": "Night shoot",
                "time_from": "2026-01-10T10:00:00+00:00",
                "time_to": "2026-01-10T11:00:00+00:00",
                "role": "ACTOR",
                "resource_type": None,
            },
        )

        await handler(command)

        assert sender.messages[0].recipient_email == "user@example.com"
        assert "Feature film" in sender.messages[0].body
        assert "http://localhost:8000/user/confirmations/token" in sender.messages[0].body
        assert "ACTOR" in sender.messages[0].body

    asyncio.run(scenario())


def test_send_email_renders_resource_type_when_present() -> None:
    async def scenario() -> None:
        sender = FakeSender()
        handler = SendNotificationEmailHandler(sender=sender)
        command = SendNotificationEmailCommand(
            recipient_email="owner@example.com",
            subject="Confirm resource reservation",
            template="reservation_confirmation",
            payload={
                "confirm_url": "http://localhost:8000/user/confirmations/token",
                "project_title": "Feature film",
                "shift_title": "Night shoot",
                "time_from": "2026-01-10T10:00:00+00:00",
                "time_to": "2026-01-10T11:00:00+00:00",
                "role": None,
                "resource_type": "camera",
            },
        )

        await handler(command)

        assert "Тип ресурса: camera" in sender.messages[0].body

    asyncio.run(scenario())


def test_send_email_renders_project_member_invitation_body() -> None:
    async def scenario() -> None:
        sender = FakeSender()
        handler = SendNotificationEmailHandler(sender=sender)
        command = SendNotificationEmailCommand(
            recipient_email="invitee@example.com",
            subject="Project invitation: Feature film",
            template="project_member_invitation",
            payload={
                "accept_url": "http://localhost:8000/user/project-invitations/token",
                "project_title": "Feature film",
                "role": "CAMERA",
                "invited_by_user_id": "director-id",
            },
        )

        await handler(command)

        assert sender.messages[0].recipient_email == "invitee@example.com"
        assert "Feature film" in sender.messages[0].body
        assert "Роль: CAMERA" in sender.messages[0].body
        assert "http://localhost:8000/user/project-invitations/token" in sender.messages[0].body

    asyncio.run(scenario())


def test_send_email_renders_shift_reminder_body_with_resources() -> None:
    async def scenario() -> None:
        sender = FakeSender()
        handler = SendNotificationEmailHandler(sender=sender)
        command = SendNotificationEmailCommand(
            recipient_email="member@example.com",
            subject="Reminder: shift 'Night shoot' starts soon",
            template="shift_reminder",
            payload={
                "shift_url": "http://localhost:8000/projects/p1/shifts/s1",
                "project_title": "Feature film",
                "shift_title": "Night shoot",
                "time_from": "2026-01-10T10:00:00+00:00",
                "time_to": "2026-01-10T18:00:00+00:00",
                "role": "CAMERA",
                "resources": "- cameras (2026-01-10 10:00 - 2026-01-10 12:00)",
            },
        )

        await handler(command)

        body = sender.messages[0].body
        assert sender.messages[0].recipient_email == "member@example.com"
        assert "Night shoot" in body
        assert "http://localhost:8000/projects/p1/shifts/s1" in body
        assert "Роль: CAMERA" in body
        assert "cameras (2026-01-10 10:00 - 2026-01-10 12:00)" in body

    asyncio.run(scenario())


def test_send_email_renders_shift_reminder_without_resources() -> None:
    async def scenario() -> None:
        sender = FakeSender()
        handler = SendNotificationEmailHandler(sender=sender)
        command = SendNotificationEmailCommand(
            recipient_email="member@example.com",
            subject="Reminder: shift 'Night shoot' starts soon",
            template="shift_reminder",
            payload={
                "shift_url": "http://localhost:8000/projects/p1/shifts/s1",
                "project_title": "Feature film",
                "shift_title": "Night shoot",
                "time_from": "2026-01-10T10:00:00+00:00",
                "time_to": "2026-01-10T18:00:00+00:00",
                "role": "DIRECTOR",
                "resources": None,
            },
        )

        await handler(command)

        assert "Ничего приносить не нужно." in sender.messages[0].body

    asyncio.run(scenario())


def test_send_email_attaches_branded_html_body() -> None:
    async def scenario() -> None:
        sender = FakeSender()
        handler = SendNotificationEmailHandler(sender=sender)
        command = SendNotificationEmailCommand(
            recipient_email="member@example.com",
            subject="Reminder: shift 'Night shoot' starts soon",
            template="shift_reminder",
            payload={
                "shift_url": "https://app.kinoflow.dev/projects/p1/shifts/s1",
                "project_title": "Feature film",
                "shift_title": "Night shoot",
                "time_from": "2026-01-10T10:00:00+00:00",
                "time_to": "2026-01-10T18:00:00+00:00",
                "role": "CAMERA",
                "resources": "- cameras (2026-01-10 10:00 - 2026-01-10 12:00)",
            },
        )

        await handler(command)

        message = sender.messages[0]
        # Plain-text fallback still present for non-HTML clients.
        assert "Night shoot" in message.body
        # Rich HTML alternative is branded and self-contained.
        assert message.html_body is not None
        assert "KinoFlow" in message.html_body
        assert ACCENT in message.html_body
        assert "https://app.kinoflow.dev/projects/p1/shifts/s1" in message.html_body
        assert "<table" in message.html_body

    asyncio.run(scenario())


def test_render_email_html_renders_reservation_confirmation() -> None:
    html = render_email_html(
        "reservation_confirmation",
        {
            "confirm_url": "https://app.kinoflow.dev/user/confirmations/token",
            "project_title": "Feature film",
            "shift_title": "Night shoot",
            "time_from": "2026-01-10T10:00:00+00:00",
            "time_to": "2026-01-10T11:00:00+00:00",
            "role": "ACTOR",
            "resource_type": None,
        },
    )
    assert "Подтвердить участие" in html  # CTA button label
    assert "https://app.kinoflow.dev/user/confirmations/token" in html
    assert "Feature film" in html
    assert "10 янв 2026, 10:00" in html  # ISO timestamps are prettified (RU months)
    assert html.startswith("<!DOCTYPE html>")


def test_render_email_html_lists_each_resource_line() -> None:
    html = render_email_html(
        "shift_reminder",
        {
            "shift_url": "https://app.kinoflow.dev/projects/p1/shifts/s1",
            "project_title": "Feature film",
            "shift_title": "Night shoot",
            "time_from": "2026-01-10T10:00:00+00:00",
            "time_to": "2026-01-10T18:00:00+00:00",
            "role": "CAMERA",
            "resources": "- cameras (10:00 - 12:00)\n- lights (10:00 - 18:00)",
        },
    )
    assert "Взять с собой" in html
    assert "cameras (10:00 - 12:00)" in html
    assert "lights (10:00 - 18:00)" in html
    # Bullet prefixes from the source string are stripped in the rendered list.
    assert "- cameras" not in html


def test_render_email_html_escapes_user_content() -> None:
    html = render_email_html(
        "project_member_invitation",
        {
            "accept_url": "https://app.kinoflow.dev/accept",
            "project_title": "<script>alert(1)</script>",
            "role": "DIRECTOR",
            "invited_by_user_id": "d1",
        },
    )
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_render_email_html_rejects_unknown_template() -> None:
    with pytest.raises(ValueError):
        render_email_html("mystery", {})


def test_taskiq_dispatcher_uses_registered_task() -> None:
    async def scenario() -> None:
        task = FakeTask()
        dispatcher = TaskiqNotificationTaskDispatcher(broker=FakeBroker(task))
        command = ScheduleNotificationEmailCommand(
            notification_id="notif-2",
            recipient_email="user@example.com",
            subject="Confirm reservation",
            template="reservation_confirmation",
            payload={"confirm_url": "http://localhost/link"},
        )

        await dispatcher.schedule_email(command)

        assert task.calls == [
            {
                "notification_id": "notif-2",
                "recipient_email": "user@example.com",
                "subject": "Confirm reservation",
                "template": "reservation_confirmation",
                "payload": {"confirm_url": "http://localhost/link"},
            }
        ]

    asyncio.run(scenario())


def test_taskiq_broker_uses_notificate_specific_transport_entities() -> None:
    settings = TaskIQ()

    broker = create_taskiq_broker("amqp://guest:guest@localhost:5672/", taskiq=settings)

    assert broker._exchange_name == "notificate.taskiq"
    assert broker._queue_name == "notificate.taskiq"
    assert broker._dead_letter_queue_name == "notificate.taskiq.dead_letter"
    assert broker._delay_queue_name == "notificate.taskiq.delay"
