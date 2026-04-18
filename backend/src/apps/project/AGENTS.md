# Project Service Agent Guide

## Read First

- Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/SPEC.md](docs/SPEC.md), and [docs/BL_LAYER.md](docs/BL_LAYER.md).
- Check [app/presentation/api.py](app/presentation/api.py), [app/presentation/broker.py](app/presentation/broker.py), and the relevant application command/query module.

## Mission

- Keep `project` responsible for projects, shifts, participants, resource requests, workflow state, and reservation outbox orchestration.

## Hard Boundaries

- Do not reimplement availability slicing or final reserve logic here.
- Do not write into `user` persistence.
- Do not bypass outbox-based async orchestration from request handlers.
- Keep V2 member-resource reads as legacy HTTP debt unless the task explicitly includes V2.

## Change Playbooks

- Reservation status change: update domain enums, serializers, state queries, broker consumers, docs, and regression tests.
- Outbox flow change: update outbox writer, poller, event consumers, docs, and interservice tests.
- Approval-state request/reply change: update broker consumers, reply payloads, token-state matching assumptions, docs, and tests.
- User-service contract change: update ACL client, schemas, dependent handlers, docs, and integration coverage.

## Known Traps

- Calling long-running cross-service reservation logic directly from HTTP handlers.
- Mixing raw enum ints and `.name` assumptions.
- Reintroducing direct HTTP for user existence or approval-state rechecks.
- Pulling user-owned resource logic into project-owned persistence or domain services.

## Validation

- Run [tests/test_project_management_service.py](tests/test_project_management_service.py).
- Run [tests/test_reservation_event_flow.py](tests/test_reservation_event_flow.py).
- Run [tests/test_user_service_http_contract.py](tests/test_user_service_http_contract.py).
- Run [tests/test_runtime_regressions.py](tests/test_runtime_regressions.py) for serialization or workflow fixes.
