from faststream.rabbit import ExchangeType, RabbitExchange, RabbitQueue

USER_EVENTS_EXCHANGE = RabbitExchange(
    name="user.events",
    type=ExchangeType.TOPIC,
    durable=True,
)

PROJECT_EVENTS_EXCHANGE = RabbitExchange(
    name="project.events",
    type=ExchangeType.TOPIC,
    durable=True,
)

NOTIFICATION_EMAIL_REQUESTED_QUEUE = RabbitQueue(
    name="notification.email_requested.notificate",
    durable=True,
    routing_key="notification.email_requested",
)
