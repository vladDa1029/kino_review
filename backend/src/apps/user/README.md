# User Service

`user` owns user-facing profile data, availability windows, user-owned resources, resource images, and final reservation facts.

## Docs

- Operational guide: [AGENTS.md](AGENTS.md)
- Architecture and contracts: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

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

4. Start the service:

```bash
uv run uvicorn main:start_app_dev --factory --reload
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
