import base64
import json
import os
import quopri
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import httpx
import pytest


pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        os.getenv("KINO_E2E") != "1",
        reason="Live cross-service E2E tests require KINO_E2E=1 and a running docker stack.",
    ),
]

GATEWAY_URL = os.getenv("KINO_E2E_GATEWAY_URL", "http://127.0.0.1:8000")
MAILHOG_API_URL = os.getenv("KINO_E2E_MAILHOG_API_URL", "http://127.0.0.1:8025/api/v2/messages")
HTTP_TIMEOUT = float(os.getenv("KINO_E2E_HTTP_TIMEOUT_SECONDS", "10"))
POLL_TIMEOUT = float(os.getenv("KINO_E2E_POLL_TIMEOUT_SECONDS", "40"))
POLL_INTERVAL = float(os.getenv("KINO_E2E_POLL_INTERVAL_SECONDS", "1"))


@dataclass(frozen=True, slots=True)
class UserSession:
    user_id: UUID
    email: str
    access_token: str

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}


def _client() -> httpx.Client:
    return httpx.Client(base_url=GATEWAY_URL, timeout=HTTP_TIMEOUT, follow_redirects=True)


def _require_live_stack() -> None:
    try:
        with _client() as client:
            response = client.get("/auth/openapi.json")
        response.raise_for_status()
        httpx.get(MAILHOG_API_URL, timeout=HTTP_TIMEOUT).raise_for_status()
    except Exception as exc:  # pragma: no cover - live env guard
        pytest.skip(f"Live stack is unavailable: {exc}")


def _register_and_login(client: httpx.Client, *, email: str, password: str) -> UserSession:
    register_response = client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )
    assert register_response.status_code == 200, register_response.text

    login_response = client.post(
        "/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login_response.status_code == 200, login_response.text
    access_token = login_response.json()["access_token"]
    user_id = _decode_token_subject(access_token)
    session = UserSession(user_id=user_id, email=email, access_token=access_token)
    _wait_for_user_projection(client, session)
    return session


def _decode_token_subject(access_token: str) -> UUID:
    payload = access_token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    decoded = base64.urlsafe_b64decode(payload.encode("ascii"))
    return UUID(json.loads(decoded.decode("utf-8"))["sub"])


def _wait_for_user_projection(client: httpx.Client, session: UserSession) -> None:
    def load_projection() -> dict:
        response = client.get(f"/user/users/me", headers=session.headers)
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["exists"] is True
        return payload

    _poll_until(load_projection)


def _poll_until(fn, *, timeout: float = POLL_TIMEOUT, interval: float = POLL_INTERVAL):
    deadline = time.monotonic() + timeout
    last_error: AssertionError | Exception | None = None
    while time.monotonic() < deadline:
        try:
            return fn()
        except AssertionError as exc:
            last_error = exc
        except Exception as exc:  # pragma: no cover - live env helper
            last_error = exc
        time.sleep(interval)
    if last_error is not None:
        raise last_error
    raise AssertionError("Polling timed out without a captured error.")


def _wait_for_confirmation_link(*, recipient_email: str, subject_fragment: str) -> str:
    def lookup() -> str:
        response = httpx.get(MAILHOG_API_URL, timeout=HTTP_TIMEOUT)
        response.raise_for_status()
        items = response.json().get("items", [])
        for item in items:
            content = item.get("Content", {})
            headers = content.get("Headers", {})
            recipients = " ".join(headers.get("To", []))
            subject = " ".join(headers.get("Subject", []))
            if recipient_email not in recipients or subject_fragment not in subject:
                continue
            body = str(content.get("Body", ""))
            decoded_body = quopri.decodestring(body.encode("utf-8")).decode(
                "utf-8",
                errors="ignore",
            )
            match = re.search(
                r"http://[^\s\"'>]+/user/confirmations/[A-Za-z0-9._-]+",
                decoded_body,
            )
            if match:
                return match.group(0)
        raise AssertionError(
            f"Did not find confirmation email for {recipient_email!r} with subject {subject_fragment!r}."
        )

    return _poll_until(lookup)


def _list_spare_times(client: httpx.Client, session: UserSession) -> list[dict]:
    response = client.get("/user/users/me/spare-times", headers=session.headers)
    assert response.status_code == 200, response.text
    return response.json()["items"]


def _list_cameras(client: httpx.Client, session: UserSession) -> list[dict]:
    response = client.get(
        "/user/users/me/cameras",
        headers=session.headers,
        params={"page": 1, "page_size": 100, "sort_dir": "asc"},
    )
    assert response.status_code == 200, response.text
    return response.json()["items"]


def _list_camera_windows(client: httpx.Client, session: UserSession, camera_id: UUID) -> list[dict]:
    response = client.get(
        f"/user/users/me/cameras/{camera_id}/free-times",
        headers=session.headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["items"]


def _assert_reserved_window_present(items: list[dict], *, time_from: datetime, time_to: datetime) -> None:
    for item in items:
        if (
            item["status"] == "reserved"
            and item["start_time"] == time_from.isoformat().replace("+00:00", "Z")
            and item["end_time"] == time_to.isoformat().replace("+00:00", "Z")
        ):
            return
    raise AssertionError("Reserved window not found yet.")


def _assert_confirmation_page(
    client: httpx.Client,
    confirm_url: str,
    *,
    expected_text: str,
) -> str:
    response = client.get(confirm_url)
    assert response.status_code == 200, response.text
    assert expected_text in response.text
    return response.text


def _future_interval() -> tuple[datetime, datetime]:
    start = (datetime.now(tz=UTC) + timedelta(hours=2)).replace(microsecond=0)
    end = start + timedelta(hours=2)
    return start, end


def _wait_for_report_ready(client: httpx.Client, session: UserSession, report_id: UUID) -> dict:
    def load_report() -> dict:
        response = client.get(f"/project/reports/{report_id}", headers=session.headers)
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["generation_status_name"] == "READY"
        return payload

    return _poll_until(load_report)


def test_member_invite_validates_user_existence_via_broker_request_reply() -> None:
    _require_live_stack()
    with _client() as client:
        suffix = uuid4().hex
        director = _register_and_login(
            client,
            email=f"director-v1-{suffix}@example.com",
            password="test-password",
        )
        invited = _register_and_login(
            client,
            email=f"invited-v1-{suffix}@example.com",
            password="test-password",
        )

        project_response = client.post(
            "/project/projects",
            headers=director.headers,
            json={"title": f"V1 validation {suffix}", "description": "broker existence check"},
        )
        assert project_response.status_code == 200, project_response.text
        project_id = UUID(project_response.json()["oid"])

        invite_existing = client.post(
            f"/project/projects/{project_id}/members",
            headers=director.headers,
            json={"user_id": str(invited.user_id), "role": "CAMERA"},
        )
        assert invite_existing.status_code == 200, invite_existing.text
        assert invite_existing.json()["user_id"] == str(invited.user_id)
        assert invite_existing.json()["status"] == 0

        invite_missing = client.post(
            f"/project/projects/{project_id}/members",
            headers=director.headers,
            json={"user_id": str(uuid4()), "role": "CAMERA"},
        )
        assert invite_missing.status_code == 404, invite_missing.text


def test_participant_reservation_confirmation_flow_end_to_end() -> None:
    _require_live_stack()
    with _client() as client:
        suffix = uuid4().hex
        director = _register_and_login(
            client,
            email=f"director-participant-{suffix}@example.com",
            password="test-password",
        )
        participant = _register_and_login(
            client,
            email=f"participant-{suffix}@example.com",
            password="test-password",
        )
        time_from, time_to = _future_interval()

        spare_time_response = client.post(
            "/user/users/me/spare-times",
            headers=participant.headers,
            json={"start_time": time_from.isoformat(), "end_time": time_to.isoformat()},
        )
        assert spare_time_response.status_code == 201, spare_time_response.text

        project_response = client.post(
            "/project/projects",
            headers=director.headers,
            json={"title": f"Participant flow {suffix}", "description": "live e2e"},
        )
        assert project_response.status_code == 200, project_response.text
        project_id = UUID(project_response.json()["oid"])

        shift_title = f"participant-shift-{suffix}"
        shift_response = client.post(
            f"/project/projects/{project_id}/shifts",
            headers=director.headers,
            json={
                "title": shift_title,
                "description": "participant flow shift",
                "start_time": time_from.isoformat(),
                "end_time": time_to.isoformat(),
            },
        )
        assert shift_response.status_code == 200, shift_response.text
        shift_id = UUID(shift_response.json()["oid"])

        invite_response = client.post(
            f"/project/shifts/{shift_id}/participants",
            headers=director.headers,
            json={
                "user_id": str(participant.user_id),
                "role": "ACTOR",
                "time_from": time_from.isoformat(),
                "time_to": time_to.isoformat(),
            },
        )
        assert invite_response.status_code == 200, invite_response.text
        participant_id = UUID(invite_response.json()["oid"])
        assert invite_response.json()["status"] == 0

        confirm_response = client.post(
            f"/project/participants/{participant_id}/confirm",
            headers=participant.headers,
        )
        assert confirm_response.status_code == 200, confirm_response.text
        assert confirm_response.json()["status"] == 15

        confirm_url = _wait_for_confirmation_link(
            recipient_email=participant.email,
            subject_fragment=f"Confirm reservation for shift '{shift_title}'",
        )
        _assert_confirmation_page(
            client,
            confirm_url,
            expected_text="Reservation confirmed",
        )

        _poll_until(
            lambda: _assert_reserved_window_present(
                _list_spare_times(client, participant),
                time_from=time_from,
                time_to=time_to,
            )
        )

        _poll_until(
            lambda: _assert_confirmation_page(
                client,
                confirm_url,
                expected_text="Already processed",
            )
        )


def test_resource_request_confirmation_flow_end_to_end() -> None:
    _require_live_stack()
    with _client() as client:
        suffix = uuid4().hex
        director = _register_and_login(
            client,
            email=f"director-resource-{suffix}@example.com",
            password="test-password",
        )
        owner = _register_and_login(
            client,
            email=f"owner-resource-{suffix}@example.com",
            password="test-password",
        )
        time_from, time_to = _future_interval()

        create_camera = client.post(
            "/user/users/me/cameras",
            headers=owner.headers,
            json={
                "title": f"Camera {suffix}",
                "description": "live e2e camera",
                "type": "mirrorless",
            },
        )
        assert create_camera.status_code == 201, create_camera.text
        cameras = _list_cameras(client, owner)
        camera = next(item for item in cameras if item["title"] == f"Camera {suffix}")
        camera_id = UUID(camera["oid"])

        create_camera_window = client.post(
            f"/user/users/me/cameras/{camera_id}/free-times",
            headers=owner.headers,
            json={"start_time": time_from.isoformat(), "end_time": time_to.isoformat()},
        )
        assert create_camera_window.status_code == 201, create_camera_window.text

        project_response = client.post(
            "/project/projects",
            headers=director.headers,
            json={"title": f"Resource flow {suffix}", "description": "live e2e"},
        )
        assert project_response.status_code == 200, project_response.text
        project_id = UUID(project_response.json()["oid"])

        shift_title = f"resource-shift-{suffix}"
        shift_response = client.post(
            f"/project/projects/{project_id}/shifts",
            headers=director.headers,
            json={
                "title": shift_title,
                "description": "resource flow shift",
                "start_time": time_from.isoformat(),
                "end_time": time_to.isoformat(),
            },
        )
        assert shift_response.status_code == 200, shift_response.text
        shift_id = UUID(shift_response.json()["oid"])

        request_response = client.post(
            f"/project/shifts/{shift_id}/resource-requests",
            headers=director.headers,
            json={
                "resource_type": "camera",
                "resource_id": str(camera_id),
                "resource_owner_user_id": str(owner.user_id),
                "time_from": time_from.isoformat(),
                "time_to": time_to.isoformat(),
            },
        )
        assert request_response.status_code == 200, request_response.text
        request_id = UUID(request_response.json()["oid"])
        assert request_response.json()["status"] == 0

        approve_response = client.post(
            f"/project/resource-requests/{request_id}/approve",
            headers=owner.headers,
        )
        assert approve_response.status_code == 200, approve_response.text
        assert approve_response.json()["status"] == 15

        confirm_url = _wait_for_confirmation_link(
            recipient_email=owner.email,
            subject_fragment=f"Confirm resource reservation for shift '{shift_title}'",
        )
        _assert_confirmation_page(
            client,
            confirm_url,
            expected_text="Reservation confirmed",
        )

        _poll_until(
            lambda: _assert_reserved_window_present(
                _list_camera_windows(client, owner, camera_id),
                time_from=time_from,
                time_to=time_to,
            )
        )

        _poll_until(
            lambda: _assert_confirmation_page(
                client,
                confirm_url,
                expected_text="Already processed",
            )
        )


def test_generated_shift_report_flow_end_to_end() -> None:
    _require_live_stack()
    with _client() as client:
        suffix = uuid4().hex
        director = _register_and_login(
            client,
            email=f"director-report-{suffix}@example.com",
            password="test-password",
        )
        time_from, time_to = _future_interval()

        project_response = client.post(
            "/project/projects",
            headers=director.headers,
            json={"title": f"Report flow {suffix}", "description": "generated report e2e"},
        )
        assert project_response.status_code == 200, project_response.text
        project_id = UUID(project_response.json()["oid"])

        shift_response = client.post(
            f"/project/projects/{project_id}/shifts",
            headers=director.headers,
            json={
                "title": f"report-shift-{suffix}",
                "description": "generated report shift",
                "start_time": time_from.isoformat(),
                "end_time": time_to.isoformat(),
            },
        )
        assert shift_response.status_code == 200, shift_response.text
        shift_id = UUID(shift_response.json()["oid"])

        approve_shift_response = client.post(
            f"/project/shifts/{shift_id}/approve",
            headers=director.headers,
        )
        assert approve_shift_response.status_code == 200, approve_shift_response.text

        generate_response = client.post(
            f"/project/shifts/{shift_id}/reports/generate",
            headers=director.headers,
        )
        assert generate_response.status_code == 200, generate_response.text
        report_id = UUID(generate_response.json()["oid"])
        assert generate_response.json()["generation_status_name"] == "PENDING"

        ready_report = _wait_for_report_ready(client, director, report_id)
        assert ready_report["version"] == 1
        assert ready_report["file_name"].endswith(".xlsx")
        assert ready_report["actuality_status_name"] == "ACTUAL"

        list_response = client.get(
            f"/project/shifts/{shift_id}/reports",
            headers=director.headers,
        )
        assert list_response.status_code == 200, list_response.text
        assert [item["oid"] for item in list_response.json()["items"]] == [str(report_id)]

        download_url_response = client.get(
            f"/project/reports/{report_id}/download-url",
            headers=director.headers,
        )
        assert download_url_response.status_code == 200, download_url_response.text
        assert ".xlsx" in download_url_response.json()["download_url"]
