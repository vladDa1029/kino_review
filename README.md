# Kino

Monorepo for project scheduling, team coordination, resources, availability, reservations, and notifications.

## Services

- `apigateway` - public HTTP edge: JWT validation, trusted identity headers, proxying, and OpenAPI aggregation.
- `auth` - credentials, access and refresh tokens, and `user.registered` events.
- `user` - user projection, profiles, resources, availability, reservations, and confirmation links.
- `project` - projects, members, shifts, resource requests, documents, and reports.
- `notificate` - email delivery requests and SMTP integration.

## Infrastructure

- PostgreSQL
- RabbitMQ
- MinIO
- MailHog

## Requirements

- Docker and Docker Compose
- Node.js 20 and npm
- Python 3.11
- Poetry
- just

## Quickstart

List available commands:

```powershell
just
```

Start the stack in the background:

```powershell
just backend
```

Start the stack in the foreground:

```powershell
just backend-dev
```

Rebuild and start backend containers:

```powershell
just backend-build
```

Start backend and frontend together:

```powershell
just all
```

Rebuild and start backend and frontend together:

```powershell
just all-build
```

## Frontend

The frontend lives in [frontend](frontend). It is a React 19 application built with Vite.

Local development:

```powershell
cd frontend
npm install
npm run dev
```

The Vite dev server runs on [http://localhost:5173](http://localhost:5173). Requests to `/api` are proxied to the API gateway at [http://localhost:8000](http://localhost:8000).

Frontend environment:

```env
VITE_API_BASE_URL=/api
```

Useful frontend commands:

```powershell
cd frontend
npm run lint
npm run build
npm run preview
```

Frontend Docker image:

```powershell
just all-build
```

The container serves the built frontend through Nginx on [http://localhost:5173](http://localhost:5173) and proxies `/api` to the `api-gateway` service.

## Backend Tests

Run tests for all backend services:

```powershell
just test-all
```

Run tests for one backend service:

```powershell
just test auth
```

Available backend services for `just test <service>`:

- `apigateway`
- `auth`
- `notificate`
- `project`
- `user`

___

![](docs/3_toad.gif)
