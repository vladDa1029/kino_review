# Notificate Architecture

## Purpose

`notificate` is a delivery-only service for outbound notifications.

It consumes notification requests, schedules background delivery, and sends email through SMTP. It does not generate tokens, validate reservation state, or move any domain entity to a new workflow status.

## Runtime Model

The service has two runtime processes built from the same composition root.

### Runtime Processes

| Process | Entrypoint | Responsibilities |
| --- | --- | --- |
| Web and broker process | [main.py](../main.py) | Expose health API, start FastStream broker, accept email-request events, dispatch background jobs |
| Task worker process | [worker.py](../worker.py) | Execute `taskiq` jobs, resolve dependencies through Dishka, send email through SMTP |

Both processes depend on:

- RabbitMQ for broker consumption and task transport;
- SMTP server for email delivery;
- shared configuration from [app/config.py](../app/config.py).

## Composition Root

Primary entrypoints:

- [main.py](../main.py)
- [worker.py](../worker.py)
- [app/bootstrap.py](../app/bootstrap.py)
- [app/ioc.py](../app/ioc.py)

Core adapters:

- [app/presentation/broker.py](../app/presentation/broker.py)
- [app/presentation/tasks.py](../app/presentation/tasks.py)
- [app/infrastructure/taskiq/dispatcher.py](../app/infrastructure/taskiq/dispatcher.py)
- [app/infrastructure/taskiq/broker.py](../app/infrastructure/taskiq/broker.py)
- [app/infrastructure/email/smtp.py](../app/infrastructure/email/smtp.py)

## Owned Data

`notificate` intentionally owns no durable business data in the current design.

| Area | Ownership | Notes |
| --- | --- | --- |
| Notification request payload | transient only | Consumed from broker and forwarded to worker |
| Email body rendering | owned by `notificate` | Presentation concern only |
| Delivery state persistence | not implemented | No local history or audit table yet |

## Inbound Interfaces

### HTTP Surface

| Path | Authentication | Purpose |
| --- | --- | --- |
| `/health` | public/internal | Liveness and service identity check |

### Consumed Events

| Routing key | Exchange | Queue | Producer | Purpose |
| --- | --- | --- | --- | --- |
| `notification.email_requested` | `user.events` | `notification.email_requested.notificate` | `user` | Request email delivery |

## Outbound Interfaces

### Template Payload Contract

| Field | Required | Notes |
| --- | --- | --- |
| `notification_id` | yes | Correlation identifier from producer |
| `recipient_email` | yes | Target email |
| `subject` | yes | Rendered subject supplied by producer |
| `template` | yes | Current value is `reservation_confirmation` |
| `payload.confirm_url` | yes | Public confirmation link |
| `payload.project_title` | yes | Used in email body |
| `payload.shift_title` | yes | Used in email body |
| `payload.time_from` | yes | ISO string for email body |
| `payload.time_to` | yes | ISO string for email body |
| `payload.role` | conditional | Present for participant approval emails |
| `payload.resource_type` | conditional | Present for resource-owner approval emails |

### Outbound Delivery Interfaces

| Interface | Adapter | Purpose |
| --- | --- | --- |
| Task dispatch | [app/infrastructure/taskiq/dispatcher.py](../app/infrastructure/taskiq/dispatcher.py) | Move delivery work off the broker consumer path |
| SMTP delivery | [app/infrastructure/email/smtp.py](../app/infrastructure/email/smtp.py) | Send final email to SMTP server or MailHog |

## Key Flows

### Email delivery flow

1. `user` emits `notification.email_requested`.
2. `notificate` consumes the event through FastStream.
3. Application logic validates the payload and enqueues a `taskiq` task.
4. The worker executes the task and sends email through the SMTP adapter.

### Local development flow

1. RabbitMQ delivers the message.
2. The worker sends SMTP traffic to MailHog or another configured SMTP server.
3. Developers inspect delivered messages without changing domain services.

## Change Playbooks

- If you change the template payload schema, update the event schema, consumer, task signature, renderer, and tests together.
- If you change the `taskiq` task contract, update both the dispatcher and the worker registration. Do not assume argument names are informal.
- If you add a new notification template, add one schema path, one rendering path, and one test path. Keep delivery-only boundaries intact.
- If you change FastStream queue bindings, update queue declarations in [app/infrastructure/broker/queues.py](../app/infrastructure/broker/queues.py) and any interservice tests that publish the event.
- If you add delivery persistence later, keep it operational. Do not let notification storage become a source of truth for project or user workflow state.

## Known Traps

- Do not turn `notificate` into a domain workflow bridge.
- Do not generate confirmation links or tokens here.
- Do not perform SMTP delivery directly inside the broker consumer; keep it in the worker path.
- Do not reinterpret notification payload semantics. `notificate` should render and deliver, not decide business meaning.
- Do not add producer-specific branching unless the contract requires it and is documented.

## Validation / Testing Focus

- Run service tests covering broker consumption, task dispatch, and SMTP adapter behavior in [tests](../tests).
- Recheck MailHog smoke after changes to template rendering or SMTP config.
- Recheck worker registration after task name or bootstrap changes.
- Recheck the consumed event schema after any producer-side payload change.

## Current Limitations

- Only email delivery is implemented.
- Only one template, `reservation_confirmation`, is implemented.
- There is no delivery persistence, bounce handling, or dead-letter strategy.
- Retry policy is generic and not template-specific.
