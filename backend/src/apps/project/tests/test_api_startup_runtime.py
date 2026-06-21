import asyncio
from types import SimpleNamespace

from fastapi import FastAPI

from app.application.commands import (
    ProcessReservationOutboxHandler,
    ProcessShiftRemindersHandler,
)
from main import lifespan


class FakeBroker:
    def __init__(self) -> None:
        self.started = 0
        self.stopped = 0

    async def start(self) -> None:
        self.started += 1

    async def stop(self) -> None:
        self.stopped += 1


class FakeTaskManager:
    def __init__(self) -> None:
        self.started = 0
        self.stopped = 0

    async def startup(self) -> None:
        self.started += 1

    async def shutdown(self) -> None:
        self.stopped += 1


class FakeHandler:
    async def __call__(self, *, limit: int) -> None:
        return None


class FakeRequestContainer:
    async def __aenter__(self) -> "FakeRequestContainer":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def get(self, dependency):
        assert dependency in (
            ProcessReservationOutboxHandler,
            ProcessShiftRemindersHandler,
        )
        return FakeHandler()


class FakeContainer:
    def __init__(self) -> None:
        self.closed = 0

    def __call__(self) -> FakeRequestContainer:
        return FakeRequestContainer()

    async def close(self) -> None:
        self.closed += 1


def test_api_lifespan_starts_and_stops_task_manager(monkeypatch) -> None:
    app = FastAPI()
    broker = FakeBroker()
    task_manager = FakeTaskManager()
    container = FakeContainer()
    prepare_calls: list[tuple[str, str, str]] = []

    async def fake_prepare_storage(*, component: str, settings) -> None:
        prepare_calls.append((component, settings.bucket, settings.endpoint_url))

    async def fake_declare_topology(*args, **kwargs) -> None:
        return None

    monkeypatch.setattr("main._prepare_storage", fake_prepare_storage)
    monkeypatch.setattr("main.declare_api_message_topology", fake_declare_topology)

    app.state._broker = broker
    app.state.reply_inbox = object()
    app.state.minio_settings = SimpleNamespace(
        bucket="reports",
        endpoint_url="http://minio:9000",
    )
    app.state.task_manager = task_manager
    app.state.dishka_container = container
    app.state.reservation_outbox = SimpleNamespace(poll_interval_seconds=60)
    app.state.shift_reminder = SimpleNamespace(poll_interval_seconds=60)

    async def exercise() -> None:
        async with lifespan(app):
            await asyncio.sleep(0)
            assert task_manager.started == 1
            assert broker.started == 1

    asyncio.run(exercise())

    assert prepare_calls == [("api", "reports", "http://minio:9000")]
    assert task_manager.stopped == 1
    assert broker.stopped == 1
    assert container.closed == 1
