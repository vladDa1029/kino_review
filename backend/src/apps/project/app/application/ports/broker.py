from typing import Any, Protocol


class EventPublisher(Protocol):
    async def publish(self, topic: str, payload: dict[str, Any]) -> None:
        raise NotImplementedError
