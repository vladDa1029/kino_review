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
uv sync
```

2. Create `.env` from `.env.example`.

3. Apply migrations:

```bash
uv run alembic upgrade head
```

4. Start the API service:

```bash
uv run uvicorn main:start_app_dev --factory --reload
```

5. Start the Taskiq worker for generated shift reports:

```bash
uv run taskiq worker worker:create_worker_taskiq_app
```

By default the OpenAPI UI is available at `http://localhost:8000/docs`.

## Migrations

Create a migration:

```bash
uv run alembic revision --autogenerate -m "message"
```

Apply migrations:

```bash
uv run alembic upgrade head
```

## Tests

Run the service test suite:

```bash
uv run pytest
```

Run lint and type checks:

```bash
uv run ruff check .
uv run mypy
```
