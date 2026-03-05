from faststream.rabbit import ExchangeType, RabbitBroker, RabbitExchange

from app.application.ports.broker import EventPublisher

PROJECT_EVENTS_EXCHANGE = RabbitExchange(
    name="project.events",
    type=ExchangeType.TOPIC,
    durable=True,
)


class RabbitPublisher(EventPublisher):
    def __init__(self, broker: RabbitBroker) -> None:
        self._broker = broker

    async def publish(self, topic: str, payload: dict) -> None:
        await self._broker.publish(
            payload,
            exchange=PROJECT_EVENTS_EXCHANGE,
            routing_key=topic,
        )
