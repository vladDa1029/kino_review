from dataclasses import dataclass
from uuid import UUID

from app.application.ports.domain import ProjectMemberRepository, ProjectRepository
from app.application.support import get_actor_member
from app.domain.entities import Project
from app.domain.errors.business import EntityNotFoundError
from app.domain.policy.member_access import ActiveMemberPolicy


@dataclass(frozen=True, slots=True, kw_only=True)
class GetProjectQuery:
    project_id: UUID
    actor_user_id: UUID


class GetProjectHandler:
    def __init__(
        self,
        *,
        projects: ProjectRepository,
        project_members: ProjectMemberRepository,
        active_member_policy: ActiveMemberPolicy,
    ) -> None:
        self._projects = projects
        self._project_members = project_members
        self._active_member_policy = active_member_policy

    async def __call__(self, query: GetProjectQuery) -> Project:
        project = await self._projects.get_by_id(query.project_id)
        if project is None:
            raise EntityNotFoundError("Project is not found.")
        actor = await get_actor_member(
            project_members=self._project_members,
            project_id=query.project_id,
            user_id=query.actor_user_id,
        )
        self._active_member_policy.check(actor, action="view project")
        return project


@dataclass(frozen=True, slots=True, kw_only=True)
class ListActorProjectsQuery:
    actor_user_id: UUID
    include_archived: bool = False


class ListActorProjectsHandler:
    def __init__(self, *, projects: ProjectRepository) -> None:
        self._projects = projects

    async def __call__(self, query: ListActorProjectsQuery) -> list[Project]:
        return await self._projects.list_by_user(
            query.actor_user_id,
            include_archived=query.include_archived,
        )
