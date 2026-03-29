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

SHIFT_PARTICIPANT_RESERVATION_CHECK_SUCCEEDED_QUEUE = RabbitQueue(
    name="shift.participant_reservation_check_succeeded.project",
    durable=True,
    routing_key="shift.participant_reservation_check_succeeded",
)

SHIFT_PARTICIPANT_RESERVATION_CHECK_FAILED_QUEUE = RabbitQueue(
    name="shift.participant_reservation_check_failed.project",
    durable=True,
    routing_key="shift.participant_reservation_check_failed",
)

SHIFT_PARTICIPANT_RESERVED_QUEUE = RabbitQueue(
    name="shift.participant_reserved.user.project",
    durable=True,
    routing_key="shift.participant_reserved.user",
)

SHIFT_PARTICIPANT_RESERVE_FAILED_QUEUE = RabbitQueue(
    name="shift.participant_reserve_failed.project",
    durable=True,
    routing_key="shift.participant_reserve_failed",
)

SHIFT_RESOURCE_REQUEST_RESERVATION_CHECK_SUCCEEDED_QUEUE = RabbitQueue(
    name="shift.resource_request_reservation_check_succeeded.project",
    durable=True,
    routing_key="shift.resource_request_reservation_check_succeeded",
)

SHIFT_RESOURCE_REQUEST_RESERVATION_CHECK_FAILED_QUEUE = RabbitQueue(
    name="shift.resource_request_reservation_check_failed.project",
    durable=True,
    routing_key="shift.resource_request_reservation_check_failed",
)

SHIFT_RESOURCE_REQUEST_RESERVED_QUEUE = RabbitQueue(
    name="shift.resource_request_reserved.user.project",
    durable=True,
    routing_key="shift.resource_request_reserved.user",
)

SHIFT_RESOURCE_REQUEST_RESERVE_FAILED_QUEUE = RabbitQueue(
    name="shift.resource_request_reserve_failed.project",
    durable=True,
    routing_key="shift.resource_request_reserve_failed",
)
