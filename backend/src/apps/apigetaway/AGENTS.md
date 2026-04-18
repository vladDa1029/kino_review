# API Gateway Agent Guide

## Read First

- Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
- Check [main.py](main.py), [app/setup.py](app/setup.py), and the route module you are changing.

## Mission

- Keep `apigetaway` edge-only: JWT validation, trusted header propagation, proxying, and OpenAPI patching.

## Hard Boundaries

- Do not add domain logic here.
- Do not add persistence or broker runtime here.
- Do not trust client-supplied `x-user-*` headers.
- Keep `/user/confirmations/*` public unless the full confirmation flow changes.

## Change Playbooks

- Public path change: update middleware public-path rules, route behavior, docs, and gateway tests.
- Trusted header or JWT claim change: update header rebuild logic, downstream expectations, and gateway tests.
- Proxy path rewrite change: keep runtime proxy behavior and patched OpenAPI behavior aligned.
- New proxied route or service: update route module, config, protected-path handling, and docs.

## Known Traps

- Breaking `/users/me` rewriting while docs still show the old shape.
- Forwarding spoofed `x-user-*` headers from clients.
- Forgetting OpenAPI patch updates when route shapes change.
- Breaking admin-only proxy rules by changing payload or header assumptions.

## Validation

- Run [tests/test_auth_headers.py](tests/test_auth_headers.py).
- Run [tests/test_auth_openapi_patch.py](tests/test_auth_openapi_patch.py).
- Run [tests/test_public_confirmation_path.py](tests/test_public_confirmation_path.py) when public-path behavior changes.
- Run [tests/test_access_denied_handler.py](tests/test_access_denied_handler.py) when auth handling changes.
