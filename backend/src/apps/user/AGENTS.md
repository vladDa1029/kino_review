# User Service Agent Guide

## Read First

- Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
- Check [app/presentation/api.py](app/presentation/api.py), [app/presentation/broker.py](app/presentation/broker.py), and the command/query module you are changing.

## Mission

- Keep `user` responsible for user projection, resources, availability, reservations, and confirmation links.

## Hard Boundaries

- Do not move project workflow state into `user`.
- Do not add cross-service foreign keys to project-owned tables.
- Keep approval links stateless unless the design is intentionally changed.
- Keep final reserve gated by broker-based approval-state recheck against `project`.

## Change Playbooks

- Confirmation-token claim change: update token encoder/decoder, confirmation endpoint, state matching, docs, and tests.
- Reservation event contract change: update project producer/consumer, user schemas, docs, and interservice tests.
- Approval-confirmation flow change: update broker handlers, confirmation endpoint, approval-state request/reply client, docs, and e2e coverage.
- Report snapshot enrichment change: update snapshot schemas, broker consumer, enrichment query, docs, and project-side contract tests together.
- Storage-backed image change: update storage adapter, HTTP upload behavior, docs, and relevant CRUD tests.

## Known Traps

- Skipping project recheck before final reserve.
- Treating `notification.email_requested` as a domain decision instead of a delivery request.
- Leaking project-owned reservation state into local persistence.
- Forgetting that `auth` owns credentials and `project` owns workflow state.
- Rendering or storing generated shift reports inside `user`.

## Validation

- Run [test/test_check_availability.py](test/test_check_availability.py).
- Run [test/test_reserve_availability.py](test/test_reserve_availability.py).
- Run [test/test_confirmation_flow.py](test/test_confirmation_flow.py) for confirmation-flow changes.
- Run [test/test_report_snapshot.py](test/test_report_snapshot.py) for report snapshot enrichment changes.
- Run relevant project and notificate integration tests when contracts change.
