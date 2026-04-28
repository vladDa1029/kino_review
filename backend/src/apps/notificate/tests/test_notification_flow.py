import asyncio

from app.application.commands.schedule_notifications import (
    ScheduleNotificationEmailCommand,
    ScheduleNotificationEmailHandler,
)
from app.application.commands.send_email import (
    SendNotificationEmailCommand,
    SendNotificationEmailHandler,
)
from app.config import TaskIQ
from app.infrastructure.taskiq.dispatcher import TaskiqNotificationTaskDispatcher
from app.infrastructure.taskiq.broker import create_taskiq_broker


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

        assert "Resource type: camera" in sender.messages[0].body

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
        assert "Role: CAMERA" in sender.messages[0].body
        assert "http://localhost:8000/user/project-invitations/token" in sender.messages[0].body

    asyncio.run(scenario())


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
