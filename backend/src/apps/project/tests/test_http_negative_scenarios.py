"""
Negative HTTP scenario tests for the project service.

Covers: 404 on missing resources, 403 on RBAC violations,
409 on state-transition conflicts, and 422 on invalid HTTP payloads.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.domain.enums import ProjectMemberStatus
from tests.test_api_crud_workflows import build_project_api_crud_context


def now_utc() -> datetime:
    return datetime.now(tz=UTC).replace(microsecond=0)


# ---------------------------------------------------------------------------
# 404 — resource not found
# ---------------------------------------------------------------------------


def test_get_nonexistent_project_returns_404() -> None:
    ctx = build_project_api_crud_context()
    owner_id = uuid4()
    try:
        with TestClient(ctx.app) as client:
            response = client.get(
                f"/projects/{uuid4()}",
                headers={"X-User-Id": str(owner_id)},
            )
    finally:
        asyncio.run(ctx.container.close())

    assert response.status_code == 404


def test_get_project_as_non_member_returns_403() -> None:
    """Non-members receive 403 (not 404) to avoid leaking project existence."""
    ctx = build_project_api_crud_context()
    owner_id = uuid4()
    outsider_id = uuid4()
    try:
        with TestClient(ctx.app) as client:
            create = client.post(
                "/projects",
                headers={"X-User-Id": str(owner_id)},
                json={"title": "Secret project", "description": ""},
            )
            project_id = create.json()["oid"]

            response = client.get(
                f"/projects/{project_id}",
                headers={"X-User-Id": str(outsider_id)},
            )
    finally:
        asyncio.run(ctx.container.close())

    assert response.status_code == 403


def test_get_nonexistent_project_member_returns_404() -> None:
    ctx = build_project_api_crud_context()
    owner_id = uuid4()
    try:
        with TestClient(ctx.app) as client:
            create = client.post(
                "/projects",
                headers={"X-User-Id": str(owner_id)},
                json={"title": "Project", "description": ""},
            )
            project_id = create.json()["oid"]

            response = client.get(
                f"/projects/{project_id}/members/{uuid4()}",
                headers={"X-User-Id": str(owner_id)},
            )
    finally:
        asyncio.run(ctx.container.close())

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# 403 — RBAC violations
# ---------------------------------------------------------------------------


def test_non_director_cannot_delete_project() -> None:
    ctx = build_project_api_crud_context()
    owner_id = uuid4()
    non_director_id = uuid4()
    try:
        with TestClient(ctx.app) as client:
            create = client.post(
                "/projects",
                headers={"X-User-Id": str(owner_id)},
                json={"title": "Owner project", "description": ""},
            )
            project_id = create.json()["oid"]

            # Invite non_director as CAMERA member (not director)
            ctx.user_service.existing_users.add(non_director_id)
            client.post(
                f"/projects/{project_id}/members",
                headers={"X-User-Id": str(owner_id)},
                json={"user_id": str(non_director_id), "role": "CAMERA"},
            )
            # Manually activate the member so the RBAC check reaches the director check
            member = asyncio.run(
                ctx.members.get_by_project_and_user(UUID(project_id), non_director_id)
            )
            if member:
                member.status = ProjectMemberStatus.ACTIVE
                asyncio.run(ctx.members.update(member))

            response = client.delete(
                f"/projects/{project_id}",
                headers={"X-User-Id": str(non_director_id)},
            )
    finally:
        asyncio.run(ctx.container.close())

    assert response.status_code == 403


def test_non_director_cannot_invite_project_member() -> None:
    ctx = build_project_api_crud_context()
    owner_id = uuid4()
    camera_user_id = uuid4()
    outsider_id = uuid4()
    try:
        with TestClient(ctx.app) as client:
            create = client.post(
                "/projects",
                headers={"X-User-Id": str(owner_id)},
                json={"title": "RBAC project", "description": ""},
            )
            project_id = create.json()["oid"]

            ctx.user_service.existing_users.add(camera_user_id)
            client.post(
                f"/projects/{project_id}/members",
                headers={"X-User-Id": str(owner_id)},
                json={"user_id": str(camera_user_id), "role": "CAMERA"},
            )
            member = asyncio.run(
                ctx.members.get_by_project_and_user(UUID(project_id), camera_user_id)
            )
            if member:
                member.status = ProjectMemberStatus.ACTIVE
                asyncio.run(ctx.members.update(member))

            ctx.user_service.existing_users.add(outsider_id)
            response = client.post(
                f"/projects/{project_id}/members",
                headers={"X-User-Id": str(camera_user_id)},
                json={"user_id": str(outsider_id), "role": "SOUND"},
            )
    finally:
        asyncio.run(ctx.container.close())

    assert response.status_code == 403


def test_non_director_cannot_change_member_role() -> None:
    ctx = build_project_api_crud_context()
    owner_id = uuid4()
    camera_user_id = uuid4()
    try:
        with TestClient(ctx.app) as client:
            create = client.post(
                "/projects",
                headers={"X-User-Id": str(owner_id)},
                json={"title": "Role RBAC project", "description": ""},
            )
            project_id = create.json()["oid"]

            ctx.user_service.existing_users.add(camera_user_id)
            client.post(
                f"/projects/{project_id}/members",
                headers={"X-User-Id": str(owner_id)},
                json={"user_id": str(camera_user_id), "role": "CAMERA"},
            )
            member = asyncio.run(
                ctx.members.get_by_project_and_user(UUID(project_id), camera_user_id)
            )
            if member:
                member.status = ProjectMemberStatus.ACTIVE
                asyncio.run(ctx.members.update(member))

            response = client.patch(
                f"/projects/{project_id}/members/{owner_id}/role",
                headers={"X-User-Id": str(camera_user_id)},
                json={"role": "SOUND"},
            )
    finally:
        asyncio.run(ctx.container.close())

    assert response.status_code == 403


def test_non_director_cannot_generate_shift_report() -> None:
    ctx = build_project_api_crud_context()
    owner_id = uuid4()
    camera_user_id = uuid4()
    try:
        with TestClient(ctx.app) as client:
            create = client.post(
                "/projects",
                headers={"X-User-Id": str(owner_id)},
                json={"title": "Report RBAC project", "description": ""},
            )
            project_id = create.json()["oid"]

            ctx.user_service.existing_users.add(camera_user_id)
            client.post(
                f"/projects/{project_id}/members",
                headers={"X-User-Id": str(owner_id)},
                json={"user_id": str(camera_user_id), "role": "CAMERA"},
            )
            member = asyncio.run(
                ctx.members.get_by_project_and_user(UUID(project_id), camera_user_id)
            )
            if member:
                member.status = ProjectMemberStatus.ACTIVE
                asyncio.run(ctx.members.update(member))

            now = now_utc()
            shift_resp = client.post(
                f"/projects/{project_id}/shifts",
                headers={"X-User-Id": str(owner_id)},
                json={
                    "title": "Shift for report",
                    "description": "",
                    "start_time": now.isoformat(),
                    "end_time": (now + timedelta(hours=2)).isoformat(),
                },
            )
            assert shift_resp.status_code == 200, shift_resp.text
            shift_id = shift_resp.json()["oid"]

            approve_resp = client.post(
                f"/shifts/{shift_id}/approve",
                headers={"X-User-Id": str(owner_id)},
            )
            assert approve_resp.status_code == 200, approve_resp.text

            response = client.post(
                f"/shifts/{shift_id}/reports/generate",
                headers={"X-User-Id": str(camera_user_id)},
            )
    finally:
        asyncio.run(ctx.container.close())

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# 409 — state transition conflicts
# ---------------------------------------------------------------------------


def test_invite_participant_outside_shift_interval_returns_409() -> None:
    ctx = build_project_api_crud_context()
    owner_id = uuid4()
    participant_id = uuid4()
    try:
        with TestClient(ctx.app) as client:
            create = client.post(
                "/projects",
                headers={"X-User-Id": str(owner_id)},
                json={"title": "Shift timing project", "description": ""},
            )
            project_id = create.json()["oid"]

            ctx.user_service.existing_users.add(participant_id)
            invite_member = client.post(
                f"/projects/{project_id}/members",
                headers={"X-User-Id": str(owner_id)},
                json={"user_id": str(participant_id), "role": "ACTOR"},
            )
            assert invite_member.status_code == 200, invite_member.text
            member = asyncio.run(
                ctx.members.get_by_project_and_user(UUID(project_id), participant_id)
            )
            if member:
                member.status = ProjectMemberStatus.ACTIVE
                asyncio.run(ctx.members.update(member))

            now = now_utc()
            shift_resp = client.post(
                f"/projects/{project_id}/shifts",
                headers={"X-User-Id": str(owner_id)},
                json={
                    "title": "Constrained shift",
                    "description": "",
                    "start_time": now.isoformat(),
                    "end_time": (now + timedelta(hours=4)).isoformat(),
                },
            )
            assert shift_resp.status_code == 200, shift_resp.text
            shift_id = shift_resp.json()["oid"]

            # time_from is BEFORE shift start — should be rejected with 409
            response = client.post(
                f"/shifts/{shift_id}/participants",
                headers={"X-User-Id": str(owner_id)},
                json={
                    "user_id": str(participant_id),
                    "role": "ACTOR",
                    "time_from": (now - timedelta(hours=1)).isoformat(),
                    "time_to": (now + timedelta(hours=2)).isoformat(),
                },
            )
    finally:
        asyncio.run(ctx.container.close())

    assert response.status_code == 409


def test_approve_shift_twice_returns_409() -> None:
    ctx = build_project_api_crud_context()
    owner_id = uuid4()
    try:
        with TestClient(ctx.app) as client:
            create = client.post(
                "/projects",
                headers={"X-User-Id": str(owner_id)},
                json={"title": "Double approve project", "description": ""},
            )
            project_id = create.json()["oid"]

            now = now_utc()
            shift_resp = client.post(
                f"/projects/{project_id}/shifts",
                headers={"X-User-Id": str(owner_id)},
                json={
                    "title": "Shift",
                    "description": "",
                    "start_time": now.isoformat(),
                    "end_time": (now + timedelta(hours=2)).isoformat(),
                },
            )
            shift_id = shift_resp.json()["oid"]

            first = client.post(
                f"/shifts/{shift_id}/approve",
                headers={"X-User-Id": str(owner_id)},
            )
            assert first.status_code == 200, first.text

            response = client.post(
                f"/shifts/{shift_id}/approve",
                headers={"X-User-Id": str(owner_id)},
            )
    finally:
        asyncio.run(ctx.container.close())

    assert response.status_code == 409


# ---------------------------------------------------------------------------
# 422 — HTTP payload validation
# ---------------------------------------------------------------------------


def test_create_project_with_missing_title_returns_422() -> None:
    ctx = build_project_api_crud_context()
    owner_id = uuid4()
    try:
        with TestClient(ctx.app) as client:
            response = client.post(
                "/projects",
                headers={"X-User-Id": str(owner_id)},
                json={"description": "no title"},
            )
    finally:
        asyncio.run(ctx.container.close())

    assert response.status_code == 422


def test_patch_project_with_empty_body_returns_409() -> None:
    """Empty PATCH body is a domain-level conflict (StateTransitionError → 409)."""
    ctx = build_project_api_crud_context()
    owner_id = uuid4()
    try:
        with TestClient(ctx.app) as client:
            create = client.post(
                "/projects",
                headers={"X-User-Id": str(owner_id)},
                json={"title": "Valid", "description": ""},
            )
            project_id = create.json()["oid"]

            response = client.patch(
                f"/projects/{project_id}",
                headers={"X-User-Id": str(owner_id)},
                json={},
            )
    finally:
        asyncio.run(ctx.container.close())

    assert response.status_code == 409


def test_invite_member_with_invalid_role_returns_422() -> None:
    ctx = build_project_api_crud_context()
    owner_id = uuid4()
    try:
        with TestClient(ctx.app) as client:
            create = client.post(
                "/projects",
                headers={"X-User-Id": str(owner_id)},
                json={"title": "Role validation", "description": ""},
            )
            project_id = create.json()["oid"]

            response = client.post(
                f"/projects/{project_id}/members",
                headers={"X-User-Id": str(owner_id)},
                json={"user_id": str(uuid4()), "role": "NONEXISTENT_ROLE"},
            )
    finally:
        asyncio.run(ctx.container.close())

    assert response.status_code == 422


def test_create_shift_with_end_before_start_returns_400_or_422() -> None:
    ctx = build_project_api_crud_context()
    owner_id = uuid4()
    try:
        with TestClient(ctx.app) as client:
            create = client.post(
                "/projects",
                headers={"X-User-Id": str(owner_id)},
                json={"title": "Time validation", "description": ""},
            )
            project_id = create.json()["oid"]

            now = now_utc()
            response = client.post(
                f"/projects/{project_id}/shifts",
                headers={"X-User-Id": str(owner_id)},
                json={
                    "title": "Bad shift",
                    "description": "",
                    "start_time": (now + timedelta(hours=2)).isoformat(),
                    "end_time": now.isoformat(),
                },
            )
    finally:
        asyncio.run(ctx.container.close())

    # Either 400 (domain invariant) or 422 (schema) — both mean rejected
    assert response.status_code in (400, 422)
