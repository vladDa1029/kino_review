# Notificate Service Agent Guide

## Read First

- Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
- Check [main.py](main.py), [worker.py](worker.py), [app/bootstrap.py](app/bootstrap.py), and the delivery module you are changing.

## Mission

- Keep `notificate` delivery-only: consume notification requests, schedule background jobs, and send SMTP email.

## Hard Boundaries

- Do not add reservation domain decisions here.
- Do not generate confirmation links or approval tokens here.
- Do not store project or user workflow state here.
- Keep FastStream for broker intake and Taskiq for background execution.

## Change Playbooks

- Template payload change: update schemas, scheduling command, send-email handler, user-side publisher, docs, and tests.
- Taskiq task contract change: update dispatcher, task registration, worker expectations, docs, and tests.
- FastStream consumer contract change: update broker schema, handler input, docs, and upstream publishers.
- New notification template: add renderer support, schema expectations, docs, and SMTP tests.

## Known Traps

- Turning `notificate` into a workflow bridge instead of a delivery service.
- Doing SMTP work directly in the broker consumer.
- Calling `project` or `user` to decide whether delivery is valid.
- Letting template payload drift from the user-side event contract.

## Validation

- Run [tests/test_notification_flow.py](tests/test_notification_flow.py).
- Run user-side integration coverage when delivery payloads change.
- Run MailHog smoke checks when SMTP rendering or worker wiring changes.
