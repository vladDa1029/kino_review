from faststream.rabbit import RabbitBroker

from app.application.ports.broker import EventPublisher
from app.infrastructure.broker.queues import PROJECT_EVENTS_EXCHANGE


class RabbitPublisher(EventPublisher):
    def __init__(self, broker: RabbitBroker) -> None:
        self._broker = broker

    async def publish(self, topic: str, payload: dict) -> None:
        await self._broker.publish(
            payload,
            exchange=PROJECT_EVENTS_EXCHANGE,
            routing_key=topic,
        )
