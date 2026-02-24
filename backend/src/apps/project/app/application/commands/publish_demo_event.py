from dataclasses import dataclass
from typing import Any

from app.application.ports.broker import EventPublisher
from app.application.ports.dispatcher import EventDispatcher


@dataclass(frozen=True, slots=True, kw_only=True)
class PublishDemoEventCommand:
    topic: str
    payload: dict[str, Any]


@dataclass(frozen=True, slots=True, kw_only=True)
class PublishDemoEventResult:
    dispatched: bool
    published: bool
    dispatch_error: str | None = None
    publish_error: str | None = None


class PublishDemoEventHandler:
    def __init__(
        self,
        dispatcher: EventDispatcher,
        publisher: EventPublisher,
    ) -> None:
        self._dispatcher = dispatcher
        self._publisher = publisher

    async def __call__(
        self,
        command: PublishDemoEventCommand,
    ) -> PublishDemoEventResult:
        try:
            await self._dispatcher.dispatch(command.topic, command.payload)
        except Exception as exc:
            return PublishDemoEventResult(
                dispatched=False,
                published=False,
                dispatch_error=str(exc),
            )

        try:
            await self._publisher.publish(command.topic, command.payload)
        except Exception as exc:
            return PublishDemoEventResult(
                dispatched=True,
                published=False,
                publish_error=str(exc),
            )

        return PublishDemoEventResult(dispatched=True, published=True)
