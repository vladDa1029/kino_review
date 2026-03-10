from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from app.domain.entities import Project, ProjectMember
from app.domain.enums import ProjectMemberStatus, ProjectRole, ProjectStatus
from app.domain.errors.business import StateTransitionError
from app.domain.policy.member_access import DirectorMemberPolicy


@dataclass
class ProjectMembershipService:
    director_policy: DirectorMemberPolicy = field(default_factory=DirectorMemberPolicy)

    def create_project(
        self,
        *,
        project_id: UUID,
        owner_membership_id: UUID,
        owner_id: UUID,
        title: str,
        description: str,
        now: datetime,
    ) -> tuple[Project, ProjectMember]:
        project = Project(
            title=title.strip(),
            description=description.strip(),
            owner_id=owner_id,
            status=ProjectStatus.ACTIVE,
            oid=project_id,
            created_at=now,
            updated_at=now,
        )
        owner_membership = ProjectMember(
            project_id=project.oid,
            user_id=owner_id,
            role=ProjectRole.DIRECTOR,
            status=ProjectMemberStatus.ACTIVE,
            invited_by=owner_id,
            oid=owner_membership_id,
            created_at=now,
            updated_at=now,
        )
        return project, owner_membership

    def invite_member(
        self,
        *,
        actor: ProjectMember,
        member_id: UUID,
        project_id: UUID,
        invited_user_id: UUID,
        invited_by: UUID,
        role: ProjectRole,
        now: datetime,
        existing: ProjectMember | None,
    ) -> ProjectMember:
        self.director_policy.check(actor, action="invite project members")
        if existing and existing.status == ProjectMemberStatus.ACTIVE:
            raise StateTransitionError("User is already an active member of the project.")

        if existing:
            existing.role = role
            existing.status = ProjectMemberStatus.INVITED
            existing.invited_by = invited_by
            existing.updated_at = now
            return existing

        return ProjectMember(
            project_id=project_id,
            user_id=invited_user_id,
            role=role,
            status=ProjectMemberStatus.INVITED,
            invited_by=invited_by,
            oid=member_id,
            created_at=now,
            updated_at=now,
        )

    def activate_member(self, member: ProjectMember, now: datetime) -> None:
        if member.status != ProjectMemberStatus.INVITED:
            raise StateTransitionError("Only invited member can be activated.")
        member.status = ProjectMemberStatus.ACTIVE
        member.updated_at = now

    def change_role(
        self,
        *,
        actor: ProjectMember,
        target: ProjectMember,
        role: ProjectRole,
        now: datetime,
    ) -> None:
        self.director_policy.check(actor, action="change project member role")
        if target.status == ProjectMemberStatus.REMOVED:
            raise StateTransitionError("Cannot change role for removed member.")
        target.role = role
        target.updated_at = now

    def remove_member(
        self,
        *,
        actor: ProjectMember,
        target: ProjectMember,
        now: datetime,
    ) -> None:
        self.director_policy.check(actor, action="remove project member")
        if target.status == ProjectMemberStatus.REMOVED:
            raise StateTransitionError("Project member is already removed.")
        target.status = ProjectMemberStatus.REMOVED
        target.updated_at = now
