from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.application.ports.domain import (
    ProjectMemberRepository,
    ResourceRequestRepository,
    ShiftRepository,
    UserServicePort,
)
from app.application.resource_access import VIEWABLE_RESOURCE_KINDS_BY_ROLE
from app.application.support import get_actor_member, require_shift
from app.domain.entities import ProjectMember, ShiftResourceRequest
from app.domain.enums import ProjectRole
from app.domain.errors.business import AccessDeniedError, EntityNotFoundError
from app.domain.policy.member_access import ActiveMemberPolicy


@dataclass(frozen=True, slots=True, kw_only=True)
class GetProjectUserResourcesQuery:
    project_id: UUID
    actor_user_id: UUID
    target_user_id: UUID


@dataclass(frozen=True, slots=True)
class ResourceTimeWindowView:
    window_id: UUID
    start_time: datetime
    end_time: datetime
    status: str


@dataclass(frozen=True, slots=True)
class ProjectResourceView:
    resource_kind: str
    resource_id: UUID
    title: str
    description: str
    resource_type: str | None
    size: str | None
    created_at: datetime | None
    windows: list[ResourceTimeWindowView]


@dataclass(frozen=True, slots=True)
class ProjectUserResourcesView:
    user_id: UUID
    role: ProjectRole
    resources: list[ProjectResourceView]


@dataclass(frozen=True, slots=True, kw_only=True)
class ListProjectMembersQuery:
    project_id: UUID
    actor_user_id: UUID
    user_id: UUID | None = None
    include_inactive: bool = False


@dataclass(frozen=True, slots=True)
class ProjectMemberView:
    oid: UUID
    user_id: UUID
    role: ProjectRole
    status: int
    invited_by: UUID
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class GetProjectMemberQuery:
    project_id: UUID
    actor_user_id: UUID
    target_user_id: UUID
    include_inactive: bool = False


class GetProjectUserResourcesHandler:
    def __init__(
        self,
        *,
        project_members: ProjectMemberRepository,
        user_service: UserServicePort,
        active_member_policy: ActiveMemberPolicy,
    ) -> None:
        self._project_members = project_members
        self._user_service = user_service
        self._active_member_policy = active_member_policy

    async def __call__(
        self,
        query: GetProjectUserResourcesQuery,
    ) -> ProjectUserResourcesView:
        actor = await get_actor_member(
            project_members=self._project_members,
            project_id=query.project_id,
            user_id=query.actor_user_id,
        )
        self._active_member_policy.check(actor, action="view project member resources")
        target = await self._require_active_target_member(
            project_id=query.project_id,
            target_user_id=query.target_user_id,
        )
        allowed_kinds = VIEWABLE_RESOURCE_KINDS_BY_ROLE.get(actor.role, ())
        if not allowed_kinds:
            raise AccessDeniedError("Actor role cannot view project member resources.")
        resources = await self._user_service.list_user_resources(
            user_id=target.user_id,
            resource_kinds=allowed_kinds,
        )
        return ProjectUserResourcesView(
            user_id=target.user_id,
            role=target.role,
            resources=[
                ProjectResourceView(
                    resource_kind=resource.resource_kind,
                    resource_id=resource.resource_id,
                    title=resource.title,
                    description=resource.description,
                    resource_type=resource.resource_type,
                    size=resource.size,
                    created_at=resource.created_at,
                    windows=[
                        ResourceTimeWindowView(
                            window_id=window.window_id,
                            start_time=window.start_time,
                            end_time=window.end_time,
                            status=window.status,
                        )
                        for window in resource.windows
                    ],
                )
                for resource in resources
            ],
        )

    async def _require_active_target_member(
        self,
        *,
        project_id: UUID,
        target_user_id: UUID,
    ) -> ProjectMember:
        target = await self._project_members.get_by_project_and_user(
            project_id=project_id,
            user_id=target_user_id,
        )
        if target is None or not target.is_active:
            raise EntityNotFoundError("Target user is not an active project member.")
        return target


class ListProjectMembersHandler:
    def __init__(
        self,
        *,
        project_members: ProjectMemberRepository,
        active_member_policy: ActiveMemberPolicy,
    ) -> None:
        self._project_members = project_members
        self._active_member_policy = active_member_policy

    async def __call__(self, query: ListProjectMembersQuery) -> list[ProjectMemberView]:
        actor = await get_actor_member(
            project_members=self._project_members,
            project_id=query.project_id,
            user_id=query.actor_user_id,
        )
        self._active_member_policy.check(actor, action="view project members")
        members = await self._project_members.list_by_project(query.project_id)
        return [
            ProjectMemberView(
                oid=member.oid,
                user_id=member.user_id,
                role=member.role,
                status=int(member.status),
                invited_by=member.invited_by,
                created_at=member.created_at,
                updated_at=member.updated_at,
            )
            for member in members
            if (query.include_inactive or member.is_active)
            and (query.user_id is None or member.user_id == query.user_id)
        ]


class GetProjectMemberHandler:
    def __init__(
        self,
        *,
        project_members: ProjectMemberRepository,
        active_member_policy: ActiveMemberPolicy,
    ) -> None:
        self._project_members = project_members
        self._active_member_policy = active_member_policy

    async def __call__(self, query: GetProjectMemberQuery) -> ProjectMemberView:
        actor = await get_actor_member(
            project_members=self._project_members,
            project_id=query.project_id,
            user_id=query.actor_user_id,
        )
        self._active_member_policy.check(actor, action="view project member")
        target = await self._project_members.get_by_project_and_user(
            project_id=query.project_id,
            user_id=query.target_user_id,
        )
        if target is None or (not query.include_inactive and not target.is_active):
            raise EntityNotFoundError("Target member is not found in project.")
        return ProjectMemberView(
            oid=target.oid,
            user_id=target.user_id,
            role=target.role,
            status=int(target.status),
            invited_by=target.invited_by,
            created_at=target.created_at,
            updated_at=target.updated_at,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ListShiftResourceRequestsQuery:
    shift_id: UUID
    actor_user_id: UUID


class ListShiftResourceRequestsHandler:
    def __init__(
        self,
        *,
        shifts: ShiftRepository,
        resource_requests: ResourceRequestRepository,
        project_members: ProjectMemberRepository,
        active_member_policy: ActiveMemberPolicy,
    ) -> None:
        self._shifts = shifts
        self._resource_requests = resource_requests
        self._project_members = project_members
        self._active_member_policy = active_member_policy

    async def __call__(
        self,
        query: ListShiftResourceRequestsQuery,
    ) -> list[ShiftResourceRequest]:
        shift = await require_shift(shifts=self._shifts, shift_id=query.shift_id)
        actor = await get_actor_member(
            project_members=self._project_members,
            project_id=shift.project_id,
            user_id=query.actor_user_id,
        )
        self._active_member_policy.check(actor, action="list shift resource requests")
        return await self._resource_requests.list_by_shift(query.shift_id)
