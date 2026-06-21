from faststream.rabbit import ExchangeType, RabbitBroker, RabbitExchange, RabbitQueue

from app.application.ports.broker import EventPublisher

PROJECT_EVENTS_EXCHANGE = RabbitExchange(
    name="project.events",
    type=ExchangeType.TOPIC,
    durable=True,
)

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

USER_EVENTS_EXCHANGE = RabbitExchange(
    name="user.events",
    type=ExchangeType.TOPIC,
    durable=True,
)

USER_EXISTENCE_REQUESTED_QUEUE = RabbitQueue(
    name="user.existence_requested.user",
    durable=True,
    routing_key="user.existence_requested",
)

USER_EMAIL_LOOKUP_REQUESTED_QUEUE = RabbitQueue(
    name="user.email_lookup_requested.user",
    durable=True,
    routing_key="user.email_lookup_requested",
)

PROJECT_MEMBER_INVITATION_REQUESTED_QUEUE = RabbitQueue(
    name="project.member_invitation_requested.user",
    durable=True,
    routing_key="project.member_invitation_requested",
)

SHIFT_PARTICIPANT_RESERVATION_CHECK_REQUESTED_QUEUE = RabbitQueue(
    name="shift.participant_reservation_check_requested.user",
    durable=True,
    routing_key="shift.participant_reservation_check_requested",
)

SHIFT_RESOURCE_REQUEST_RESERVATION_CHECK_REQUESTED_QUEUE = RabbitQueue(
    name="shift.resource_request_reservation_check_requested.user",
    durable=True,
    routing_key="shift.resource_request_reservation_check_requested",
)

SHIFT_PARTICIPANT_APPROVAL_REQUESTED_QUEUE = RabbitQueue(
    name="shift.participant_approval_requested.user",
    durable=True,
    routing_key="shift.participant_approval_requested",
)

SHIFT_RESOURCE_REQUEST_APPROVAL_REQUESTED_QUEUE = RabbitQueue(
    name="shift.resource_request_approval_requested.user",
    durable=True,
    routing_key="shift.resource_request_approval_requested",
)

SHIFT_PARTICIPANT_RESERVATION_REQUESTED_QUEUE = RabbitQueue(
    name="shift.participant_reservation_requested.user",
    durable=True,
    routing_key="shift.participant_reservation_requested",
)

SHIFT_RESOURCE_REQUEST_RESERVATION_REQUESTED_QUEUE = RabbitQueue(
    name="shift.resource_request_reservation_requested.user",
    durable=True,
    routing_key="shift.resource_request_reservation_requested",
)

SHIFT_REPORT_SNAPSHOT_REQUESTED_QUEUE = RabbitQueue(
    name="shift.report_snapshot_requested.user",
    durable=True,
    routing_key="shift.report_snapshot_requested",
)

SHIFT_REMINDER_REQUESTED_QUEUE = RabbitQueue(
    name="shift.reminder_requested.user",
    durable=True,
    routing_key="shift.reminder_requested",
)


class RabbitPublisher(EventPublisher):
    def __init__(self, broker: RabbitBroker) -> None:
        self._broker = broker

    async def publish(self, topic: str, payload: dict) -> None:
        await self._broker.publish(
            payload,
            exchange=USER_EVENTS_EXCHANGE,
            routing_key=topic,
        )
