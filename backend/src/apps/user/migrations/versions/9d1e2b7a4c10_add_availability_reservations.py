"""add availability reservations

Revision ID: 9d1e2b7a4c10
Revises: 672045836ce9
Create Date: 2026-03-08 12:05:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9d1e2b7a4c10"
down_revision: Union[str, Sequence[str], None] = "672045836ce9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "availability_reservations",
        sa.Column("oid", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("obj_id", sa.UUID(), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reservation_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.oid"],
            name=op.f("fk_availability_reservations_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("oid", name=op.f("pk_availability_reservations")),
    )


def downgrade() -> None:
    op.drop_table("availability_reservations")
