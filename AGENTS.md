# Monorepo Agent Guide

## Read First

- Use the nearest nested `AGENTS.md` as the primary operational guide.
- Use service `docs/ARCHITECTURE.md` for contracts, interfaces, tables, and flow details.
- Use `README.md` only for quickstart, local run, migrations, and tests.

## Cross-Service Rules

- Keep service ownership boundaries intact. Do not move logic across services for convenience.
- Do not introduce direct database coupling between services.
- Do not add cross-service foreign keys or ORM relationships to tables owned by another service.
- Treat `apigetaway` as the only public edge for JWT validation and trusted identity headers.
- Treat internal HTTP endpoints as internal-only. Preserve internal auth requirements.

## Contract Changes

- Update producer and consumer in the same pass.
- Update schema objects, tests, and docs in the same pass.
- Keep event names stable unless the contract is intentionally versioned or migrated everywhere.
- If a token claim or trusted header changes, update every downstream reader.

## Documentation Rules

- Keep `AGENTS.md` strict and short.
- Keep `ARCHITECTURE.md` as the source of truth for interfaces, state tables, playbooks, and traps.
- Keep Markdown links GitHub-relative only.
- Keep agent-facing docs in English and ASCII-first.

## Validation

- Run tests in every touched service.
- Run interservice tests when event contracts, internal HTTP contracts, auth claims, or trusted headers change.
- Add regression coverage for contract bugs, not only unit coverage for isolated helpers.
