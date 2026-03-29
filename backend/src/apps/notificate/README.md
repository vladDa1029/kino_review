# Notificate Service

`notificate` is an internal delivery service for outbound notifications.

Current responsibility:
- consume `notification.email_requested` events from `user.events`
- enqueue email delivery in `taskiq`
- execute SMTP delivery in a dedicated worker

The service does not own reservation domain logic. It does not decide whether a reservation is valid and it does not generate confirmation links. Those responsibilities live in `user` and `project`.

## Current Architecture

High-level flow:

```text
user.events -> faststream consumer -> application handler -> taskiq dispatcher
-> taskiq worker -> SMTP adapter -> MailHog/SMTP server
```

Main layers:
- `app/presentation`
  - FastAPI health API
  - FastStream broker consumer
  - Taskiq task entrypoints
- `app/application`
  - use cases for scheduling and sending notifications
  - ports for task dispatching and email delivery
- `app/infrastructure`
  - SMTP adapter
  - Taskiq broker factory and dispatcher adapter
- `app/bootstrap.py`
  - shared composition root for web app and worker
- `main.py`
  - HTTP app factory
- `worker.py`
  - Taskiq worker factory

## Implemented Now

Implemented features:
- `notification.email_requested` contract consumption
- `reservation_confirmation` email template
- SMTP delivery through `smtplib`
- `taskiq` worker with `dishka` integration
- shared bootstrap for web app and worker
- retry middleware for background tasks
- MailHog support in local Docker environment
- health endpoint: `GET /health`

Implemented event payload fields for `reservation_confirmation`:
- `notification_id`
- `recipient_email`
- `subject`
- `template`
- `payload.confirm_url`
- `payload.project_title`
- `payload.shift_title`
- `payload.time_from`
- `payload.time_to`
- `payload.role`
- `payload.resource_type`

Not implemented here by design:
- reservation approval decisions
- confirmation token generation
- pending approval persistence
- project state transitions

## Important Files

Core entrypoints:
- [main.py](main.py)
- [worker.py](worker.py)
- [app/bootstrap.py](app/bootstrap.py)

Presentation layer:
- [app/presentation/broker.py](app/presentation/broker.py)
- [app/presentation/tasks.py](app/presentation/tasks.py)
- [app/presentation/schemas.py](app/presentation/schemas.py)

Application layer:
- [app/application/commands/schedule_notifications.py](app/application/commands/schedule_notifications.py)
- [app/application/commands/send_email.py](app/application/commands/send_email.py)

Infrastructure layer:
- [app/infrastructure/taskiq/dispatcher.py](app/infrastructure/taskiq/dispatcher.py)
- [app/infrastructure/taskiq/broker.py](app/infrastructure/taskiq/broker.py)
- [app/infrastructure/email/smtp.py](app/infrastructure/email/smtp.py)

More detailed docs:
- [ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [reservation-email-approval-flow.md](../../../../docs/reservation-email-approval-flow.md)

## Local Run

Run API:

```bash
poetry run python -m uvicorn main:start_app_dev --factory --host 0.0.0.0 --port 8005
```

Run worker:

```bash
poetry run taskiq worker worker:create_worker_taskiq_app
```

## Tests

Service tests:

```bash
poetry run pytest -q
```

Interservice smoke is documented in:
- [reservation-email-approval-flow.md](../../../../docs/reservation-email-approval-flow.md)
