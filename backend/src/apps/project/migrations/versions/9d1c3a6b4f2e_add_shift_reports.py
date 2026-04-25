"""add shift reports

Revision ID: 9d1c3a6b4f2e
Revises: 2336d6388735
Create Date: 2026-04-21 18:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "9d1c3a6b4f2e"
down_revision: Union[str, Sequence[str], None] = "2336d6388735"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "shift_reports",
        sa.Column("oid", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("shift_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("generation_status", sa.Integer(), nullable=False),
        sa.Column("actuality_status", sa.Integer(), nullable=False),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("file_name", sa.String(length=512), nullable=True),
        sa.Column("bucket", sa.String(length=255), nullable=True),
        sa.Column("storage_key", sa.String(length=1024), nullable=True),
        sa.Column("mime_type", sa.String(length=255), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.String(length=2000), nullable=True),
        sa.Column("stale_reason", sa.String(length=255), nullable=True),
        sa.Column("stale_marked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.oid"],
            name=op.f("fk_shift_reports_project_id_projects"),
        ),
        sa.ForeignKeyConstraint(
            ["shift_id"],
            ["shift.oid"],
            name=op.f("fk_shift_reports_shift_id_shift"),
        ),
        sa.PrimaryKeyConstraint("oid", name=op.f("pk_shift_reports")),
        sa.UniqueConstraint("shift_id", "version", name=op.f("uq_shift_reports_shift_id")),
        sa.UniqueConstraint("storage_key", name=op.f("uq_shift_reports_storage_key")),
    )
    op.create_index(op.f("ix_shift_reports_project_id"), "shift_reports", ["project_id"], unique=False)
    op.create_index(op.f("ix_shift_reports_shift_id"), "shift_reports", ["shift_id"], unique=False)
    op.create_index(
        op.f("ix_shift_reports_generation_status"),
        "shift_reports",
        ["generation_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_shift_reports_actuality_status"),
        "shift_reports",
        ["actuality_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_shift_reports_actuality_status"), table_name="shift_reports")
    op.drop_index(op.f("ix_shift_reports_generation_status"), table_name="shift_reports")
    op.drop_index(op.f("ix_shift_reports_shift_id"), table_name="shift_reports")
    op.drop_index(op.f("ix_shift_reports_project_id"), table_name="shift_reports")
    op.drop_table("shift_reports")
