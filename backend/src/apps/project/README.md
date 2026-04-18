# Project Service

`project` owns projects, membership, shifts, documents, resource requests, and reservation workflow state.

## Docs

- Operational guide: [AGENTS.md](AGENTS.md)
- Architecture and contracts: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Product and domain spec: [docs/SPEC.md](docs/SPEC.md)
- Business-layer notes: [docs/BL_LAYER.md](docs/BL_LAYER.md)

## Local Run

1. Install dependencies:

```bash
poetry install
```

2. Create `.env` from `.env.example`.

3. Apply migrations:

```bash
poetry run alembic upgrade head
```

4. Start the service:

```bash
poetry run uvicorn main:start_app_dev --factory --reload
```

By default the OpenAPI UI is available at `http://localhost:8000/docs`.

## Migrations

Create a migration:

```bash
poetry run alembic revision --autogenerate -m "message"
```

Apply migrations:

```bash
poetry run alembic upgrade head
```

## Tests

Run the service test suite:

```bash
poetry run pytest
```
