from faststream.rabbit import ExchangeType, RabbitExchange, RabbitQueue

USER_REGISTERED_EXCHANGE = RabbitExchange(
    name="user.registered",
    type=ExchangeType.TOPIC,
    durable=True,
)

USER_REGISTERED_QUEUE = RabbitQueue(
    name="user.registered.user",
    durable=True,
    routing_key="user.registered",
)
