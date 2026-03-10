from faststream.rabbit import ExchangeType, RabbitExchange, RabbitQueue

USER_EVENTS_EXCHANGE = RabbitExchange(
    name="user.events",
    type=ExchangeType.TOPIC,
    durable=True,
)

PROJECT_MEMBER_APPROVED_QUEUE = RabbitQueue(
    name="project.member.approved.project",
    durable=True,
    routing_key="project.member.approved",
)
