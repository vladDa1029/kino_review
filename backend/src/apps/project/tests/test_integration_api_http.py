import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx
import pytest
from dishka import AsyncContainer, Provider, Scope, make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.application.commands import UpdateProjectHandler
from app.application.queries import GetProjectHandler
from app.application.support import SystemClock
from app.config import UserService
from app.domain.entities import Project, ProjectMember
from app.domain.enums import ProjectMemberStatus, ProjectRole, ProjectStatus
from app.domain.errors.base import ApplicationError
from app.domain.errors.business import EntityNotFoundError, ExternalServiceError
from app.domain.policy import ActiveMemberPolicy, DirectorMemberPolicy
from app.presentation import handlers
from app.presentation.api import router as project_router
from app.presentation.http.user_service import UserServiceHttpClient


class InMemoryProjectRepo:
    def __init__(self, projects: dict[UUID, Project]) -> None:
        self._projects = projects

    async def add(self, project: Project) -> None:
        self._projects[project.oid] = project

    async def get_by_id(self, project_id: UUID) -> Project | None:
        return self._projects.get(project_id)

    async def list_by_user(self, user_id: UUID, *, include_archived: bool = False) -> list[Project]:
        result = [item for item in self._projects.values() if item.owner_id == user_id]
        if include_archived:
            return result
        return [item for item in result if item.status != ProjectStatus.ARCHIVED]

    async def update(self, project: Project) -> None:
        self._projects[project.oid] = project


class InMemoryProjectMemberRepo:
    def __init__(self, members: dict[tuple[UUID, UUID], ProjectMember]) -> None:
        self._members = members

    async def add(self, member: ProjectMember) -> None:
        self._members[(member.project_id, member.user_id)] = member

    async def list_by_project(self, project_id: UUID) -> list[ProjectMember]:
        return [
            item
            for (candidate_project_id, _), item in self._members.items()
            if candidate_project_id == project_id
        ]

    async def get_by_project_and_user(
        self,
        project_id: UUID,
        user_id: UUID,
    ) -> ProjectMember | None:
        return self._members.get((project_id, user_id))

    async def update(self, member: ProjectMember) -> None:
        self._members[(member.project_id, member.user_id)] = member


class FakeTx:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class FakePublisher:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, topic: str, payload: dict) -> None:
        self.events.append((topic, payload))


@dataclass(slots=True)
class ApiIntegrationContext:
    app: FastAPI
    container: AsyncContainer
    tx: FakeTx
    publisher: FakePublisher
    projects: InMemoryProjectRepo


def build_api_integration_context(
    *,
    project: Project,
    actor: ProjectMember,
) -> ApiIntegrationContext:
    projects = InMemoryProjectRepo({project.oid: project})
    members = InMemoryProjectMemberRepo({(actor.project_id, actor.user_id): actor})
    tx = FakeTx()
    publisher = FakePublisher()

    get_project_handler = GetProjectHandler(
        projects=projects,
        project_members=members,
        active_member_policy=ActiveMemberPolicy(),
    )
    update_project_handler = UpdateProjectHandler(
        transaction_manager=tx,
        clock=SystemClock(),
        publisher=publisher,
        projects=projects,
        project_members=members,
        director_member_policy=DirectorMemberPolicy(),
    )

    provider = Provider(scope=Scope.REQUEST)
    provider.provide(
        source=lambda: get_project_handler,
        provides=GetProjectHandler,
        scope=Scope.REQUEST,
    )
    provider.provide(
        source=lambda: update_project_handler,
        provides=UpdateProjectHandler,
        scope=Scope.REQUEST,
    )

    container = make_async_container(provider)
    app = FastAPI()
    setup_dishka(container=container, app=app)
    app.add_exception_handler(ApplicationError, handlers.application_error_handler)
    app.include_router(project_router)
    return ApiIntegrationContext(
        app=app,
        container=container,
        tx=tx,
        publisher=publisher,
        projects=projects,
    )


def test_integration_get_project_endpoint_returns_payload() -> None:
    now = datetime.now(tz=UTC)
    project_id = uuid4()
    actor_id = uuid4()
    project = Project(
        oid=project_id,
        title="Integration title",
        description="Integration description",
        owner_id=actor_id,
        status=ProjectStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    actor = ProjectMember(
        oid=uuid4(),
        project_id=project_id,
        user_id=actor_id,
        role=ProjectRole.DIRECTOR,
        status=ProjectMemberStatus.ACTIVE,
        invited_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    ctx = build_api_integration_context(project=project, actor=actor)

    try:
        with TestClient(ctx.app) as client:
            response = client.get(
                f"/projects/{project_id}",
                headers={"X-User-Id": str(actor_id)},
            )
    finally:
        asyncio.run(ctx.container.close())

    assert response.status_code == 200
    payload = response.json()
    assert payload["oid"] == str(project_id)
    assert payload["title"] == "Integration title"
    assert payload["owner_id"] == str(actor_id)


def test_integration_patch_project_rejects_empty_payload_and_blank_title() -> None:
    now = datetime.now(tz=UTC)
    project_id = uuid4()
    actor_id = uuid4()
    project = Project(
        oid=project_id,
        title="Original title",
        description="Original description",
        owner_id=actor_id,
        status=ProjectStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    actor = ProjectMember(
        oid=uuid4(),
        project_id=project_id,
        user_id=actor_id,
        role=ProjectRole.DIRECTOR,
        status=ProjectMemberStatus.ACTIVE,
        invited_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    ctx = build_api_integration_context(project=project, actor=actor)

    try:
        with TestClient(ctx.app) as client:
            empty_payload_response = client.patch(
                f"/projects/{project_id}",
                headers={"X-User-Id": str(actor_id)},
                json={},
            )
            blank_title_response = client.patch(
                f"/projects/{project_id}",
                headers={"X-User-Id": str(actor_id)},
                json={"title": "   "},
            )
    finally:
        asyncio.run(ctx.container.close())

    assert empty_payload_response.status_code == 409
    assert (
        empty_payload_response.json()["detail"] == "At least one field must be provided for update."
    )
    assert blank_title_response.status_code == 409
    assert blank_title_response.json()["detail"] == "Project title cannot be empty."
    assert ctx.projects._projects[project_id].title == "Original title"
    assert ctx.tx.commits == 0
    assert ctx.tx.rollbacks == 1
    assert not ctx.publisher.events


def test_integration_user_service_client_uses_resource_free_times_paths(monkeypatch) -> None:
    user_id = uuid4()
    resource_id = uuid4()
    window_id = uuid4()
    calls: list[str] = []

    class FakeAsyncClient:
        def __init__(self, *, base_url: str, timeout: float) -> None:
            self._base_url = base_url.rstrip("/")
            self._timeout = timeout

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def request(
            self,
            *,
            method: str,
            url: str,
            json: dict | None = None,
            params: dict | None = None,
            headers: dict[str, str] | None = None,
        ) -> httpx.Response:
            del json, params, headers, self._timeout
            calls.append(url)
            request = httpx.Request(method=method, url=f"{self._base_url}{url}")
            if url == f"/users/{user_id}/microfons":
                return httpx.Response(
                    200,
                    request=request,
                    json={
                        "items": [
                            {
                                "oid": str(resource_id),
                                "title": "Mic",
                                "description": "Shotgun",
                                "type": "dynamic",
                                "size": "M",
                                "create_at": "2026-03-05T10:00:00Z",
                            }
                        ]
                    },
                )
            if url == f"/users/{user_id}/microfons/{resource_id}/free-times":
                return httpx.Response(
                    200,
                    request=request,
                    json={
                        "items": [
                            {
                                "oid": str(window_id),
                                "start_time": "2026-03-05T11:00:00Z",
                                "end_time": "2026-03-05T12:00:00Z",
                                "status": "free",
                            }
                        ]
                    },
                )
            return httpx.Response(
                404,
                request=request,
                json={"detail": "Not found"},
            )

    monkeypatch.setattr(
        "app.presentation.http.user_service.httpx.AsyncClient",
        FakeAsyncClient,
    )

    settings = UserService(
        USER_SERVICE_BASE_URL="http://user.test",
        USER_SERVICE_TIMEOUT_SECONDS=1,
    )
    client = UserServiceHttpClient(settings=settings, publisher=FakePublisher())

    resources = asyncio.run(
        client.list_user_resources(
            user_id=user_id,
            resource_kinds=("microfons",),
        )
    )

    assert len(resources) == 1
    assert resources[0].resource_id == resource_id
    assert len(resources[0].windows) == 1
    assert f"/users/{user_id}/microfons/{resource_id}/free-times" in calls
    assert not any("/resources/" in path for path in calls)


def test_integration_user_service_client_collects_paginated_resources(monkeypatch) -> None:
    user_id = uuid4()
    resource_1 = uuid4()
    resource_2 = uuid4()
    resource_3 = uuid4()

    class FakeAsyncClient:
        def __init__(self, *, base_url: str, timeout: float) -> None:
            self._base_url = base_url.rstrip("/")
            self._timeout = timeout

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def request(
            self,
            *,
            method: str,
            url: str,
            json: dict | None = None,
            params: dict | None = None,
            headers: dict[str, str] | None = None,
        ) -> httpx.Response:
            del json, headers, self._timeout
            request = httpx.Request(method=method, url=f"{self._base_url}{url}")
            page = (params or {}).get("page")
            if url == f"/users/{user_id}/microfons" and page == 1:
                return httpx.Response(
                    200,
                    request=request,
                    json={
                        "items": [
                            {
                                "oid": str(resource_1),
                                "title": "Mic-1",
                                "description": "D1",
                                "type": "dynamic",
                                "size": "M",
                                "create_at": "2026-03-05T10:00:00Z",
                            },
                            {
                                "oid": str(resource_2),
                                "title": "Mic-2",
                                "description": "D2",
                                "type": "dynamic",
                                "size": "M",
                                "create_at": "2026-03-05T10:01:00Z",
                            },
                        ],
                        "pages": 2,
                    },
                )
            if url == f"/users/{user_id}/microfons" and page == 2:
                return httpx.Response(
                    200,
                    request=request,
                    json={
                        "items": [
                            {
                                "oid": str(resource_3),
                                "title": "Mic-3",
                                "description": "D3",
                                "type": "dynamic",
                                "size": "M",
                                "create_at": "2026-03-05T10:02:00Z",
                            }
                        ],
                        "pages": 2,
                    },
                )
            if url.startswith(f"/users/{user_id}/microfons/") and url.endswith("/free-times"):
                return httpx.Response(
                    200,
                    request=request,
                    json={
                        "items": [
                            {
                                "oid": str(uuid4()),
                                "start_time": "2026-03-05T11:00:00Z",
                                "end_time": "2026-03-05T12:00:00Z",
                                "status": "free",
                            }
                        ]
                    },
                )
            return httpx.Response(404, request=request, json={"detail": "Not found"})

    monkeypatch.setattr(
        "app.presentation.http.user_service.httpx.AsyncClient",
        FakeAsyncClient,
    )

    settings = UserService(
        USER_SERVICE_BASE_URL="http://user.test",
        USER_SERVICE_TIMEOUT_SECONDS=1,
    )
    client = UserServiceHttpClient(settings=settings, publisher=FakePublisher())

    resources = asyncio.run(
        client.list_user_resources(
            user_id=user_id,
            resource_kinds=("microfons",),
        )
    )

    assert len(resources) == 3
    assert {item.resource_id for item in resources} == {resource_1, resource_2, resource_3}


def test_integration_user_service_client_raises_on_free_times_method_mismatch(monkeypatch) -> None:
    user_id = uuid4()
    resource_id = uuid4()

    class FakeAsyncClient:
        def __init__(self, *, base_url: str, timeout: float) -> None:
            self._base_url = base_url.rstrip("/")
            self._timeout = timeout

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def request(
            self,
            *,
            method: str,
            url: str,
            json: dict | None = None,
            params: dict | None = None,
            headers: dict[str, str] | None = None,
        ) -> httpx.Response:
            del json, params, headers, self._timeout
            request = httpx.Request(method=method, url=f"{self._base_url}{url}")
            if url == f"/users/{user_id}/microfons":
                return httpx.Response(
                    200,
                    request=request,
                    json={
                        "items": [
                            {
                                "oid": str(resource_id),
                                "title": "Mic",
                                "description": "Shotgun",
                                "type": "dynamic",
                                "size": "M",
                                "create_at": "2026-03-05T10:00:00Z",
                            }
                        ],
                        "pages": 1,
                    },
                )
            if url == f"/users/{user_id}/microfons/{resource_id}/free-times":
                return httpx.Response(
                    405,
                    request=request,
                    json={"detail": "Method not allowed"},
                )
            return httpx.Response(404, request=request, json={"detail": "Not found"})

    monkeypatch.setattr(
        "app.presentation.http.user_service.httpx.AsyncClient",
        FakeAsyncClient,
    )

    settings = UserService(
        USER_SERVICE_BASE_URL="http://user.test",
        USER_SERVICE_TIMEOUT_SECONDS=1,
    )
    client = UserServiceHttpClient(settings=settings, publisher=FakePublisher())

    with pytest.raises(ExternalServiceError):
        asyncio.run(
            client.list_user_resources(
                user_id=user_id,
                resource_kinds=("microfons",),
            )
        )


def test_integration_user_service_client_does_not_fallback_to_spare_times(monkeypatch) -> None:
    user_id = uuid4()
    resource_id = uuid4()
    calls: list[str] = []

    class FakeAsyncClient:
        def __init__(self, *, base_url: str, timeout: float) -> None:
            self._base_url = base_url.rstrip("/")
            self._timeout = timeout

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def request(
            self,
            *,
            method: str,
            url: str,
            json: dict | None = None,
            params: dict | None = None,
            headers: dict[str, str] | None = None,
        ) -> httpx.Response:
            del json, params, headers, self._timeout
            calls.append(url)
            request = httpx.Request(method=method, url=f"{self._base_url}{url}")
            if url == f"/users/{user_id}/microfons":
                return httpx.Response(
                    200,
                    request=request,
                    json={
                        "items": [
                            {
                                "oid": str(resource_id),
                                "title": "Mic",
                                "description": "Shotgun",
                                "type": "dynamic",
                                "size": "M",
                                "create_at": "2026-03-05T10:00:00Z",
                            }
                        ],
                    },
                )
            if url == f"/users/{user_id}/microfons/{resource_id}/free-times":
                return httpx.Response(404, request=request, json={"detail": "Not found"})
            if url == f"/users/{user_id}/spare-times":
                return httpx.Response(200, request=request, json={"items": []})
            return httpx.Response(404, request=request, json={"detail": "Not found"})

    monkeypatch.setattr(
        "app.presentation.http.user_service.httpx.AsyncClient",
        FakeAsyncClient,
    )

    settings = UserService(
        USER_SERVICE_BASE_URL="http://user.test",
        USER_SERVICE_TIMEOUT_SECONDS=1,
    )
    client = UserServiceHttpClient(settings=settings, publisher=FakePublisher())

    with pytest.raises(EntityNotFoundError):
        asyncio.run(
            client.list_user_resources(
                user_id=user_id,
                resource_kinds=("microfons",),
            )
        )

    assert f"/users/{user_id}/spare-times" not in calls


def test_integration_user_service_client_raises_when_pagination_limit_reached(
    monkeypatch,
) -> None:
    user_id = uuid4()

    class FakeAsyncClient:
        def __init__(self, *, base_url: str, timeout: float) -> None:
            self._base_url = base_url.rstrip("/")
            self._timeout = timeout

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def request(
            self,
            *,
            method: str,
            url: str,
            json: dict | None = None,
            params: dict | None = None,
            headers: dict[str, str] | None = None,
        ) -> httpx.Response:
            del json, headers, self._timeout
            request = httpx.Request(method=method, url=f"{self._base_url}{url}")
            if url == f"/users/{user_id}/microfons":
                return httpx.Response(
                    200,
                    request=request,
                    json={
                        "items": [
                            {
                                "oid": str(uuid4()),
                                "title": f"Mic-{(params or {}).get('page', 1)}",
                                "description": "D",
                                "type": "dynamic",
                                "size": "M",
                                "create_at": "2026-03-05T10:00:00Z",
                            }
                        ],
                    },
                )
            if "/free-times" in url:
                return httpx.Response(200, request=request, json={"items": []})
            return httpx.Response(404, request=request, json={"detail": "Not found"})

    monkeypatch.setattr(
        "app.presentation.http.user_service.httpx.AsyncClient",
        FakeAsyncClient,
    )
    monkeypatch.setattr(UserServiceHttpClient, "_RESOURCE_PAGE_SIZE", 1)
    monkeypatch.setattr(UserServiceHttpClient, "_RESOURCE_MAX_PAGES", 2)

    settings = UserService(
        USER_SERVICE_BASE_URL="http://user.test",
        USER_SERVICE_TIMEOUT_SECONDS=1,
    )
    client = UserServiceHttpClient(settings=settings, publisher=FakePublisher())

    with pytest.raises(ExternalServiceError):
        asyncio.run(
            client.list_user_resources(
                user_id=user_id,
                resource_kinds=("microfons",),
            )
        )
