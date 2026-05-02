set shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command"]

services := "apigateway auth notificate project user"
backend_compose := "-f docker-compose.yaml"
all_compose := "-f docker-compose.yaml -f frontend/docker-compose.frontend.yaml"

# Show available commands.
default:
    @just --list

# Show available commands.
help:
    @just --list

# Run backend services in background.
run:
    docker compose {{backend_compose}} up -d

# Run backend services in foreground.
run-dev:
    docker compose {{backend_compose}} up

# Pull, rebuild, and start backend services.
build:
    git pull
    docker compose {{backend_compose}} up --build -d

# Run backend services in background.
backend:
    docker compose {{backend_compose}} up -d

# Run backend services in foreground.
backend-dev:
    docker compose {{backend_compose}} up

# Rebuild and start backend services.
backend-build:
    docker compose {{backend_compose}} up --build -d

# Run backend and frontend in background.
all:
    docker compose {{all_compose}} up -d

# Run backend and frontend in foreground.
all-dev:
    docker compose {{all_compose}} up

# Rebuild and start backend and frontend.
all-build:
    docker compose {{all_compose}} up --build -d

# Sync dependencies for one backend service. Usage: just sync auth
sync service:
    uv sync --directory backend/src/apps/{{service}}

# Sync dependencies for all backend services.
sync-all:
    @$ErrorActionPreference = "Stop"; $services = "{{services}}".Split(" "); foreach ($service in $services) { Write-Host ""; Write-Host "==> $service"; uv sync --directory "backend/src/apps/$service" }

# Check the lockfile for one backend service. Usage: just lock-check auth
lock-check service:
    uv lock --check --directory backend/src/apps/{{service}}

# Run Ruff for one backend service. Usage: just lint auth
lint service:
    uv run --directory backend/src/apps/{{service}} ruff check .

# Run mypy for one backend service. Usage: just typecheck auth
typecheck service:
    uv run --directory backend/src/apps/{{service}} mypy

# Run tests for one backend service. Usage: just test auth
test service:
    uv run --directory backend/src/apps/{{service}} pytest

# Run tests for all backend services.
test-all:
    @$ErrorActionPreference = "Stop"; $services = "{{services}}".Split(" "); foreach ($service in $services) { Write-Host ""; Write-Host "==> $service"; uv run --directory "backend/src/apps/$service" pytest }

# Run Ruff, mypy, and tests for one backend service. Usage: just check auth
check service:
    uv run --directory backend/src/apps/{{service}} ruff check .
    uv run --directory backend/src/apps/{{service}} mypy
    uv run --directory backend/src/apps/{{service}} pytest

# Run Ruff, mypy, and tests for all backend services.
check-all:
    @$ErrorActionPreference = "Stop"; $services = "{{services}}".Split(" "); foreach ($service in $services) { Write-Host ""; Write-Host "==> $service"; uv run --directory "backend/src/apps/$service" ruff check .; uv run --directory "backend/src/apps/$service" mypy; uv run --directory "backend/src/apps/$service" pytest }
