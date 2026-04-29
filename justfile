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

# Run tests for one backend service. Usage: just test auth
test service:
    @Push-Location "backend/src/apps/{{service}}"; try { poetry run pytest } finally { Pop-Location }

# Run tests for all backend services.
test-all:
    @$ErrorActionPreference = "Stop"; $services = "{{services}}".Split(" "); foreach ($service in $services) { Write-Host ""; Write-Host "==> $service"; Push-Location "backend/src/apps/$service"; try { poetry run pytest } finally { Pop-Location } }
