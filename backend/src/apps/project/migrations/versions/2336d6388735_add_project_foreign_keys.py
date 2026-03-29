"""add project foreign keys

Revision ID: 2336d6388735
Revises: 6b1f3c7d9a20
Create Date: 2026-03-26 16:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "2336d6388735"
down_revision: Union[str, Sequence[str], None] = "6b1f3c7d9a20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_foreign_key(
        op.f("fk_users_project_role_project_id_projects"),
        "users_project_role",
        "projects",
        ["project_id"],
        ["oid"],
    )
    op.create_foreign_key(
        op.f("fk_shift_project_id_projects"),
        "shift",
        "projects",
        ["project_id"],
        ["oid"],
    )
    op.create_foreign_key(
        op.f("fk_shift_participants_shift_id_shift"),
        "shift_participants",
        "shift",
        ["shift_id"],
        ["oid"],
    )
    op.create_foreign_key(
        op.f("fk_documents_shift_id_shift"),
        "documents",
        "shift",
        ["shift_id"],
        ["oid"],
    )
    op.create_foreign_key(
        op.f("fk_shift_resource_requests_project_id_projects"),
        "shift_resource_requests",
        "projects",
        ["project_id"],
        ["oid"],
    )
    op.create_foreign_key(
        op.f("fk_shift_resource_requests_shift_id_shift"),
        "shift_resource_requests",
        "shift",
        ["shift_id"],
        ["oid"],
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_shift_resource_requests_shift_id_shift"),
        "shift_resource_requests",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_shift_resource_requests_project_id_projects"),
        "shift_resource_requests",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_documents_shift_id_shift"),
        "documents",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_shift_participants_shift_id_shift"),
        "shift_participants",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_shift_project_id_projects"),
        "shift",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_users_project_role_project_id_projects"),
        "users_project_role",
        type_="foreignkey",
    )
