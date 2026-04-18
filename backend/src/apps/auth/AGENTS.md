# Auth Service Agent Guide

## Read First

- Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
- Check [main.py](main.py), [app/presentations/api.py](app/presentations/api.py), and [app/application/use_case/authenticate_uc.py](app/application/use_case/authenticate_uc.py).

## Mission

- Keep `auth` responsible for credentials, tokens, and `user.registered`.

## Hard Boundaries

- Do not add profile, availability, or project workflow state here.
- Keep password hashing and JWT creation in infrastructure/security adapters.
- Preserve `user.registered` unless every consumer is updated together.
- Treat gateway claim readers as part of the auth contract.

## Change Playbooks

- JWT claim change: update token creation, token validation readers, gateway behavior, docs, and tests.
- Refresh-cookie change: update HTTP behavior, gateway expectations if needed, and auth tests.
- `user.registered` payload change: update producer, user consumer, schemas, docs, and interservice tests.
- Admin access change: update trusted-header assumptions, access checks, and auth plus gateway tests.

## Known Traps

- Changing claim names without updating `apigetaway`.
- Assuming logout implies token revocation.
- Mixing profile logic into auth-user persistence.
- Changing registration event shape without updating `user`.

## Validation

- Run [tests/test_admin_access.py](tests/test_admin_access.py).
- Run [tests/test_access_denied_handler.py](tests/test_access_denied_handler.py).
- Run gateway tests too when claims or trusted-header expectations change.
