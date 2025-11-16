from faststream.rabbit import ExchangeType, RabbitExchange


USER_REGISTERED_EXCHANGE = RabbitExchange(
    name="user.registered",
    type=ExchangeType.TOPIC,
    durable=True,  # или DIRECT
)
