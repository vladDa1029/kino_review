# Notificate Service

`notificate` is an internal delivery service for outbound email notifications.

## Docs

- Operational guide: [AGENTS.md](AGENTS.md)
- Architecture and runtime model: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Cross-service approval flow: [../../../../docs/reservation-email-approval-flow.md](../../../../docs/reservation-email-approval-flow.md)

## Local Run

Run the API and broker process:

```bash
poetry run uvicorn main:start_app_dev --factory --reload --host 0.0.0.0 --port 8005
```

Run the worker:

```bash
poetry run taskiq worker worker:create_worker_taskiq_app
```

For local delivery tests, point SMTP settings to MailHog or another local SMTP server.

## Tests

Run the service test suite:

```bash
poetry run pytest -q
```
