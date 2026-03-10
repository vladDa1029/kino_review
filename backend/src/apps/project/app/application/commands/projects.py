from dataclasses import dataclass
from uuid import UUID

from app.application.ports.broker import EventPublisher
from app.application.ports.domain import (
    ClockPort,
    IdGeneratorPort,
    ProjectMemberRepository,
    ProjectRepository,
    UserServicePort,
)
from app.application.ports.transaction import TransactionManager
from app.application.support import get_actor_member, publish_best_effort
from app.domain.entities import Project, ProjectMember
from app.domain.enums import ProjectMemberStatus, ProjectRole, ProjectStatus
from app.domain.errors.business import EntityNotFoundError, StateTransitionError
from app.domain.policy import DirectorMemberPolicy
from app.domain.services import ProjectMembershipService


@dataclass(frozen=True, slots=True, kw_only=True)
class CreateProjectCommand:
    owner_id: UUID
    title: str
    description: str = ""


class CreateProjectHandler:
    def __init__(
        self,
        *,
        transaction_manager: TransactionManager,
        clock: ClockPort,
        id_generator: IdGeneratorPort,
        publisher: EventPublisher,
        user_service: UserServicePort,
        projects: ProjectRepository,
        project_members: ProjectMemberRepository,
        membership_service: ProjectMembershipService,
    ) -> None:
        self._tx = transaction_manager
        self._clock = clock
        self._id_generator = id_generator
        self._publisher = publisher
        self._user_service = user_service
        self._projects = projects
        self._project_members = project_members
        self._membership_service = membership_service

    async def __call__(self, command: CreateProjectCommand) -> Project:
        now = self._clock.now()
        try:
            await self._user_service.ensure_user_exists(command.owner_id)
            project, owner_member = self._membership_service.create_project(
                project_id=self._id_generator(),
                owner_membership_id=self._id_generator(),
                owner_id=command.owner_id,
                title=command.title,
                description=command.description,
                now=now,
            )
            await self._projects.add(project)
            await self._project_members.add(owner_member)
            await self._tx.commit()
        except Exception:
            await self._tx.rollback()
            raise

        await publish_best_effort(
            publisher=self._publisher,
            topic="project.created",
            payload={
                "project_id": str(project.oid),
                "owner_id": str(command.owner_id),
                "title": project.title,
            },
        )
        return project


@dataclass(frozen=True, slots=True, kw_only=True)
class DeleteProjectCommand:
    project_id: UUID
    actor_user_id: UUID


class DeleteProjectHandler:
    def __init__(
        self,
        *,
        transaction_manager: TransactionManager,
        clock: ClockPort,
        publisher: EventPublisher,
        projects: ProjectRepository,
        project_members: ProjectMemberRepository,
        director_member_policy: DirectorMemberPolicy,
    ) -> None:
        self._tx = transaction_manager
        self._clock = clock
        self._publisher = publisher
        self._projects = projects
        self._project_members = project_members
        self._director_member_policy = director_member_policy

    async def __call__(self, command: DeleteProjectCommand) -> Project:
        now = self._clock.now()
        try:
            project = await self._projects.get_by_id(command.project_id)
            if project is None:
                raise EntityNotFoundError("Project is not found.")

            actor = await get_actor_member(
                project_members=self._project_members,
                project_id=command.project_id,
                user_id=command.actor_user_id,
            )
            self._director_member_policy.check(actor, action="archive project")

            if project.status == ProjectStatus.ARCHIVED:
                raise StateTransitionError("Project is already archived.")

            project.status = ProjectStatus.ARCHIVED
            project.updated_at = now

            await self._projects.update(project)
            await self._tx.commit()
        except Exception:
            await self._tx.rollback()
            raise

        await publish_best_effort(
            publisher=self._publisher,
            topic="project.archived",
            payload={
                "project_id": str(project.oid),
                "archived_by": str(command.actor_user_id),
            },
        )
        return project


@dataclass(frozen=True, slots=True, kw_only=True)
class UpdateProjectCommand:
    project_id: UUID
    actor_user_id: UUID
    title: str | None = None
    description: str | None = None


class UpdateProjectHandler:
    def __init__(
        self,
        *,
        transaction_manager: TransactionManager,
        clock: ClockPort,
        publisher: EventPublisher,
        projects: ProjectRepository,
        project_members: ProjectMemberRepository,
        director_member_policy: DirectorMemberPolicy,
    ) -> None:
        self._tx = transaction_manager
        self._clock = clock
        self._publisher = publisher
        self._projects = projects
        self._project_members = project_members
        self._director_member_policy = director_member_policy

    async def __call__(self, command: UpdateProjectCommand) -> Project:
        if command.title is None and command.description is None:
            raise StateTransitionError("At least one field must be provided for update.")

        now = self._clock.now()
        try:
            project = await self._projects.get_by_id(command.project_id)
            if project is None:
                raise EntityNotFoundError("Project is not found.")
            if project.status == ProjectStatus.ARCHIVED:
                raise StateTransitionError("Cannot update archived project.")

            actor = await get_actor_member(
                project_members=self._project_members,
                project_id=command.project_id,
                user_id=command.actor_user_id,
            )
            self._director_member_policy.check(actor, action="update project")

            if command.title is not None:
                normalized_title = command.title.strip()
                if not normalized_title:
                    raise StateTransitionError("Project title cannot be empty.")
                project.title = normalized_title
            if command.description is not None:
                project.description = command.description.strip()
            project.updated_at = now

            await self._projects.update(project)
            await self._tx.commit()
        except Exception:
            await self._tx.rollback()
            raise

        await publish_best_effort(
            publisher=self._publisher,
            topic="project.updated",
            payload={
                "project_id": str(project.oid),
                "updated_by": str(command.actor_user_id),
            },
        )
        return project


@dataclass(frozen=True, slots=True, kw_only=True)
class InviteProjectMemberCommand:
    project_id: UUID
    actor_user_id: UUID
    invited_user_id: UUID
    role: ProjectRole


class InviteProjectMemberHandler:
    def __init__(
        self,
        *,
        transaction_manager: TransactionManager,
        clock: ClockPort,
        id_generator: IdGeneratorPort,
        publisher: EventPublisher,
        user_service: UserServicePort,
        project_members: ProjectMemberRepository,
        projects: ProjectRepository,
        membership_service: ProjectMembershipService,
    ) -> None:
        self._tx = transaction_manager
        self._clock = clock
        self._id_generator = id_generator
        self._publisher = publisher
        self._user_service = user_service
        self._project_members = project_members
        self._projects = projects
        self._membership_service = membership_service

    async def __call__(self, command: InviteProjectMemberCommand) -> ProjectMember:
        now = self._clock.now()
        try:
            project = await self._projects.get_by_id(command.project_id)
            if project is None:
                raise EntityNotFoundError("Project is not found.")
            await self._user_service.ensure_user_exists(command.invited_user_id)
            actor = await get_actor_member(
                project_members=self._project_members,
                project_id=command.project_id,
                user_id=command.actor_user_id,
            )
            existing = await self._project_members.get_by_project_and_user(
                project_id=command.project_id,
                user_id=command.invited_user_id,
            )
            member = self._membership_service.invite_member(
                actor=actor,
                member_id=self._id_generator(),
                project_id=command.project_id,
                invited_user_id=command.invited_user_id,
                invited_by=command.actor_user_id,
                role=command.role,
                now=now,
                existing=existing,
            )
            if existing is None:
                await self._project_members.add(member)
            else:
                await self._project_members.update(member)
            await self._tx.commit()
        except Exception:
            await self._tx.rollback()
            raise

        await publish_best_effort(
            publisher=self._publisher,
            topic="project.member_invited",
            payload={
                "project_id": str(command.project_id),
                "invited_user_id": str(command.invited_user_id),
                "role": int(command.role),
                "invited_by": str(command.actor_user_id),
            },
        )
        return member


@dataclass(frozen=True, slots=True, kw_only=True)
class ApproveProjectMemberInvitationCommand:
    project_id: UUID
    user_id: UUID
    approved_by_user_id: UUID | None = None


class ApproveProjectMemberInvitationHandler:
    def __init__(
        self,
        *,
        transaction_manager: TransactionManager,
        clock: ClockPort,
        publisher: EventPublisher,
        project_members: ProjectMemberRepository,
        membership_service: ProjectMembershipService,
    ) -> None:
        self._tx = transaction_manager
        self._clock = clock
        self._publisher = publisher
        self._project_members = project_members
        self._membership_service = membership_service

    async def __call__(
        self, command: ApproveProjectMemberInvitationCommand
    ) -> ProjectMember | None:
        member = await self._project_members.get_by_project_and_user(
            project_id=command.project_id,
            user_id=command.user_id,
        )
        if member is None or member.status != ProjectMemberStatus.INVITED:
            return member

        now = self._clock.now()
        try:
            self._membership_service.activate_member(member=member, now=now)
            await self._project_members.update(member)
            await self._tx.commit()
        except Exception:
            await self._tx.rollback()
            raise

        await publish_best_effort(
            publisher=self._publisher,
            topic="project.member_activated",
            payload={
                "project_id": str(member.project_id),
                "user_id": str(member.user_id),
                "approved_by": str(command.approved_by_user_id or command.user_id),
            },
        )
        return member


@dataclass(frozen=True, slots=True, kw_only=True)
class ChangeProjectMemberRoleCommand:
    project_id: UUID
    actor_user_id: UUID
    target_user_id: UUID
    role: ProjectRole


class ChangeProjectMemberRoleHandler:
    def __init__(
        self,
        *,
        transaction_manager: TransactionManager,
        clock: ClockPort,
        publisher: EventPublisher,
        project_members: ProjectMemberRepository,
        membership_service: ProjectMembershipService,
    ) -> None:
        self._tx = transaction_manager
        self._clock = clock
        self._publisher = publisher
        self._project_members = project_members
        self._membership_service = membership_service

    async def __call__(self, command: ChangeProjectMemberRoleCommand) -> ProjectMember:
        now = self._clock.now()
        try:
            actor = await get_actor_member(
                project_members=self._project_members,
                project_id=command.project_id,
                user_id=command.actor_user_id,
            )
            target = await self._project_members.get_by_project_and_user(
                project_id=command.project_id,
                user_id=command.target_user_id,
            )
            if target is None:
                raise EntityNotFoundError("Target member is not found in project.")
            self._membership_service.change_role(
                actor=actor,
                target=target,
                role=command.role,
                now=now,
            )
            await self._project_members.update(target)
            await self._tx.commit()
        except Exception:
            await self._tx.rollback()
            raise

        await publish_best_effort(
            publisher=self._publisher,
            topic="project.member_role_changed",
            payload={
                "project_id": str(command.project_id),
                "user_id": str(command.target_user_id),
                "role": int(command.role),
                "changed_by": str(command.actor_user_id),
            },
        )
        return target


@dataclass(frozen=True, slots=True, kw_only=True)
class RemoveProjectMemberCommand:
    project_id: UUID
    actor_user_id: UUID
    target_user_id: UUID


class RemoveProjectMemberHandler:
    def __init__(
        self,
        *,
        transaction_manager: TransactionManager,
        clock: ClockPort,
        publisher: EventPublisher,
        projects: ProjectRepository,
        project_members: ProjectMemberRepository,
        membership_service: ProjectMembershipService,
    ) -> None:
        self._tx = transaction_manager
        self._clock = clock
        self._publisher = publisher
        self._projects = projects
        self._project_members = project_members
        self._membership_service = membership_service

    async def __call__(self, command: RemoveProjectMemberCommand) -> ProjectMember:
        now = self._clock.now()
        try:
            project = await self._projects.get_by_id(command.project_id)
            if project is None:
                raise EntityNotFoundError("Project is not found.")

            actor = await get_actor_member(
                project_members=self._project_members,
                project_id=command.project_id,
                user_id=command.actor_user_id,
            )
            target = await self._project_members.get_by_project_and_user(
                project_id=command.project_id,
                user_id=command.target_user_id,
            )
            if target is None:
                raise EntityNotFoundError("Target member is not found in project.")
            if target.user_id == project.owner_id:
                raise StateTransitionError("Cannot remove project owner.")

            self._membership_service.remove_member(
                actor=actor,
                target=target,
                now=now,
            )
            await self._project_members.update(target)
            await self._tx.commit()
        except Exception:
            await self._tx.rollback()
            raise

        await publish_best_effort(
            publisher=self._publisher,
            topic="project.member_removed",
            payload={
                "project_id": str(command.project_id),
                "user_id": str(command.target_user_id),
                "removed_by": str(command.actor_user_id),
            },
        )
        return target
