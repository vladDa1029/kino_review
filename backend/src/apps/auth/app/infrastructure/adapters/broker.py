from typing import AsyncIterator
from faststream.rabbit import RabbitBroker, ExchangeType, RabbitExchange

from app.config import Rabbitmq


USER_REGISTERED_EXCHANGE = RabbitExchange(
    name="user.registered",
    type=ExchangeType.TOPIC,
    durable=True,  # или DIRECT
)


async def get_rabbit_broker(settings: Rabbitmq) -> AsyncIterator[RabbitBroker]:
    broker = RabbitBroker(
        url=settings.url,
    )

    await broker.start()
    await broker.declare_exchange(USER_REGISTERED_EXCHANGE)
    yield broker
    await broker.stop()
