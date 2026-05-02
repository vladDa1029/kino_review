import logging
from datetime import datetime
from uuid import UUID, uuid4

import httpx

from app.application.ports.broker import EventPublisher
from app.application.ports.domain import (
    UserIdentity,
    UserResourceItem,
    UserResourceTimeWindow,
    UserServicePort,
)
from app.config import UserService
from app.domain.errors.business import EntityNotFoundError, ExternalServiceError
from app.infrastructure.broker.request_reply import BrokerReplyInbox
from app.presentation.schemas import BrokerUserEmailLookupReply, BrokerUserExistenceReply

USER_EXISTENCE_REQUESTED_TOPIC = "user.existence_requested"
USER_EXISTENCE_PROVIDED = "user.existence_provided"
USER_EXISTENCE_FAILED = "user.existence_failed"
USER_EMAIL_LOOKUP_REQUESTED_TOPIC = "user.email_lookup_requested"
USER_EMAIL_LOOKUP_PROVIDED = "user.email_lookup_provided"
USER_EMAIL_LOOKUP_FAILED = "user.email_lookup_failed"


class UserServiceHttpClient(UserServicePort):
    _RESOURCE_PAGE_SIZE = 100
    _RESOURCE_MAX_PAGES = 1000
    _RESOURCE_KIND_PATHS: dict[str, str] = {
        "microfons": "/users/{user_id}/microfons",
        "cameras": "/users/{user_id}/cameras",
        "camera-tripods": "/users/{user_id}/camera-tripods",
        "lights": "/users/{user_id}/lights",
        "light-tripods": "/users/{user_id}/light-tripods",
        "sounds": "/users/{user_id}/sounds",
        "requisites": "/users/{user_id}/requisites",
    }
    _RESOURCE_WINDOWS_PATHS: dict[str, str] = {
        "microfons": "/users/{user_id}/microfons/{resource_id}/free-times",
        "cameras": "/users/{user_id}/cameras/{resource_id}/free-times",
        "camera-tripods": "/users/{user_id}/camera-tripods/{resource_id}/free-times",
        "lights": "/users/{user_id}/lights/{resource_id}/free-times",
        "light-tripods": "/users/{user_id}/light-tripods/{resource_id}/free-times",
        "sounds": "/users/{user_id}/sounds/{resource_id}/free-times",
        "requisites": "/users/{user_id}/requisites/{resource_id}/free-times",
    }
    _log = logging.getLogger(__name__)

    def __init__(
        self,
        settings: UserService,
        publisher: EventPublisher,
        reply_inbox: BrokerReplyInbox | None = None,
    ) -> None:
        self._settings = settings
        self._publisher = publisher
        self._reply_inbox = reply_inbox or BrokerReplyInbox(service_name="project")

    async def ensure_user_exists(self, user_id: UUID) -> None:
        correlation_id = str(uuid4())
        self._reply_inbox.register(correlation_id)
        try:
            await self._publisher.publish(
                USER_EXISTENCE_REQUESTED_TOPIC,
                {
                    "correlation_id": correlation_id,
                    "reply_topic": self._reply_inbox.reply_topic,
                    "user_id": str(user_id),
                },
            )
        except Exception as exc:
            self._reply_inbox.discard(correlation_id)
            raise ExternalServiceError(f"User-service existence request publish failed: {exc}") from exc

        try:
            payload = await self._reply_inbox.wait_for(
                correlation_id,
                timeout=self._settings.timeout_seconds,
            )
        except TimeoutError as exc:
            raise ExternalServiceError("User-service existence reply timed out.") from exc

        try:
            event = BrokerUserExistenceReply.model_validate(payload)
        except Exception as exc:
            raise ExternalServiceError("User-service existence reply payload is invalid.") from exc

        if str(event.correlation_id) != correlation_id:
            raise ExternalServiceError("User-service existence reply correlation mismatch.")
        if event.response_type == USER_EXISTENCE_FAILED:
            raise ExternalServiceError(
                event.reason or "User-service existence request failed."
            )
        if event.exists is False:
            raise EntityNotFoundError(f"User {user_id} does not exist.")
        if event.exists is not True:
            raise ExternalServiceError("User-service existence reply is missing 'exists'.")

    async def get_user_by_email(self, email: str) -> UserIdentity:
        normalized_email = email.strip()
        correlation_id = str(uuid4())
        self._reply_inbox.register(correlation_id)
        try:
            await self._publisher.publish(
                USER_EMAIL_LOOKUP_REQUESTED_TOPIC,
                {
                    "correlation_id": correlation_id,
                    "reply_topic": self._reply_inbox.reply_topic,
                    "email": normalized_email,
                },
            )
        except Exception as exc:
            self._reply_inbox.discard(correlation_id)
            raise ExternalServiceError(f"User-service email lookup publish failed: {exc}") from exc

        try:
            payload = await self._reply_inbox.wait_for(
                correlation_id,
                timeout=self._settings.timeout_seconds,
            )
        except TimeoutError as exc:
            raise ExternalServiceError("User-service email lookup reply timed out.") from exc

        try:
            event = BrokerUserEmailLookupReply.model_validate(payload)
        except Exception as exc:
            raise ExternalServiceError("User-service email lookup reply payload is invalid.") from exc

        if str(event.correlation_id) != correlation_id:
            raise ExternalServiceError("User-service email lookup reply correlation mismatch.")
        if event.response_type == USER_EMAIL_LOOKUP_FAILED:
            raise ExternalServiceError(event.reason or "User-service email lookup failed.")
        if event.exists is False or event.user_id is None:
            raise EntityNotFoundError(f"User with email {normalized_email} does not exist.")
        if event.exists is not True:
            raise ExternalServiceError("User-service email lookup reply is missing 'exists'.")
        return UserIdentity(user_id=event.user_id, email=event.email)

    async def list_user_resources(
        self,
        *,
        user_id: UUID,
        resource_kinds: tuple[str, ...],
    ) -> list[UserResourceItem]:
        resources: list[UserResourceItem] = []
        headers = {"X-User-Id": str(user_id)}
        for kind in resource_kinds:
            path_template = self._RESOURCE_KIND_PATHS.get(kind)
            if path_template is None:
                continue
            seen_resource_ids: set[str] = set()
            fully_loaded = False
            for page in range(1, self._RESOURCE_MAX_PAGES + 1):
                data = await self._request(
                    "GET",
                    path_template.format(user_id=user_id),
                    params={
                        "page": page,
                        "page_size": self._RESOURCE_PAGE_SIZE,
                    },
                    headers=headers,
                )
                items = data.get("items", [])
                if not isinstance(items, list) or not items:
                    fully_loaded = True
                    break

                for item in items:
                    resource_id = item.get("oid")
                    if not resource_id or resource_id in seen_resource_ids:
                        continue
                    seen_resource_ids.add(resource_id)
                    created_raw = item.get("create_at")
                    created_at = None
                    if isinstance(created_raw, str):
                        created_at = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
                    windows = await self._list_resource_windows(
                        user_id=user_id,
                        resource_kind=kind,
                        resource_id=resource_id,
                        headers=headers,
                    )
                    resources.append(
                        UserResourceItem(
                            resource_kind=kind,
                            resource_id=UUID(resource_id),
                            title=str(item.get("title", "")),
                            description=str(item.get("description", "")),
                            resource_type=item.get("type"),
                            size=item.get("size"),
                            created_at=created_at,
                            windows=tuple(windows),
                        )
                    )

                pages = data.get("pages")
                if isinstance(pages, int):
                    if page >= pages:
                        fully_loaded = True
                        break
                elif len(items) < self._RESOURCE_PAGE_SIZE:
                    fully_loaded = True
                    break
            if not fully_loaded:
                self._log.warning(
                    "resource.pagination.limit_reached",
                    extra={
                        "user_id": str(user_id),
                        "resource_kind": kind,
                        "max_pages": self._RESOURCE_MAX_PAGES,
                    },
                )
                raise ExternalServiceError(
                    f"User-service pagination limit exceeded for '{kind}' resources."
                )
        return resources

    async def ensure_user_resource_exists(
        self,
        *,
        user_id: UUID,
        resource_kind: str,
        resource_id: UUID,
    ) -> None:
        resources = await self.list_user_resources(
            user_id=user_id,
            resource_kinds=(resource_kind,),
        )
        if not any(resource.resource_id == resource_id for resource in resources):
            raise EntityNotFoundError("Resource is not found for user.")

    async def reserve_user_time(
        self,
        *,
        request_id: UUID,
        user_id: UUID,
        time_from: datetime,
        time_to: datetime,
        project_id: UUID,
        shift_id: UUID,
        entity_id: UUID,
    ) -> None:
        await self._publisher.publish(
            "shift.participant_reservation_check_requested",
            {
                "request_id": str(request_id),
                "project_id": str(project_id),
                "shift_id": str(shift_id),
                "participant_id": str(entity_id),
                "user_id": str(user_id),
                "start_time": time_from.isoformat(),
                "end_time": time_to.isoformat(),
            },
        )

    async def reserve_resource_time(
        self,
        *,
        request_id: UUID,
        owner_user_id: UUID,
        resource_id: UUID,
        time_from: datetime,
        time_to: datetime,
        project_id: UUID,
        shift_id: UUID,
        entity_id: UUID,
    ) -> None:
        await self._publisher.publish(
            "shift.resource_request_reservation_check_requested",
            {
                "request_id": str(request_id),
                "project_id": str(project_id),
                "shift_id": str(shift_id),
                "resource_request_id": str(entity_id),
                "owner_user_id": str(owner_user_id),
                "resource_id": str(resource_id),
                "start_time": time_from.isoformat(),
                "end_time": time_to.isoformat(),
            },
        )

    async def _request(
        self,
        method: str,
        path: str,
        json: dict | None = None,
        params: dict | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict:
        try:
            async with httpx.AsyncClient(
                base_url=self._settings.base_url.rstrip("/"),
                timeout=self._settings.timeout_seconds,
            ) as client:
                response = await client.request(
                    method=method,
                    url=path,
                    json=json,
                    params=params,
                    headers=headers,
                )
        except httpx.HTTPError as exc:
            raise ExternalServiceError(f"User-service call failed: {exc}") from exc

        if response.status_code == 404:
            raise EntityNotFoundError("Requested entity was not found in user-service.")

        if response.is_error:
            raise ExternalServiceError(
                f"User-service returned {response.status_code}: {response.text}"
            )

        if not response.content:
            return {}
        return response.json()

    async def _list_resource_windows(
        self,
        *,
        user_id: UUID,
        resource_kind: str,
        resource_id: str,
        headers: dict[str, str],
    ) -> list[UserResourceTimeWindow]:
        windows_path_template = self._RESOURCE_WINDOWS_PATHS.get(resource_kind)
        if windows_path_template is None:
            return []
        data = await self._request(
            "GET",
            windows_path_template.format(user_id=user_id, resource_id=resource_id),
            headers=headers,
        )
        windows: list[UserResourceTimeWindow] = []
        for item in data.get("items", []):
            window_id = item.get("oid")
            start_time_raw = item.get("start_time")
            end_time_raw = item.get("end_time")
            if (
                not window_id
                or not isinstance(start_time_raw, str)
                or not isinstance(end_time_raw, str)
            ):
                continue
            windows.append(
                UserResourceTimeWindow(
                    window_id=UUID(window_id),
                    start_time=datetime.fromisoformat(start_time_raw.replace("Z", "+00:00")),
                    end_time=datetime.fromisoformat(end_time_raw.replace("Z", "+00:00")),
                    status=str(item.get("status", "")),
                )
            )
        return windows
