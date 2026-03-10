"""add reservation outbox

Revision ID: 6b1f3c7d9a20
Revises: eb839239e502
Create Date: 2026-03-08 12:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6b1f3c7d9a20"
down_revision: Union[str, Sequence[str], None] = "eb839239e502"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reservation_outbox",
        sa.Column("oid", sa.Uuid(), nullable=False),
        sa.Column("operation", sa.String(length=64), nullable=False),
        sa.Column("aggregate_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.String(length=2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("oid", name=op.f("pk_reservation_outbox")),
    )
    op.create_index(
        op.f("ix_reservation_outbox_aggregate_id"),
        "reservation_outbox",
        ["aggregate_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_reservation_outbox_status"),
        "reservation_outbox",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_reservation_outbox_status"), table_name="reservation_outbox")
    op.drop_index(op.f("ix_reservation_outbox_aggregate_id"), table_name="reservation_outbox")
    op.drop_table("reservation_outbox")
