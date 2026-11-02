"""chat mute

Revision ID: c3a9e5b7d1f2
Revises: b7e2d4f1a9c0
Create Date: 2026-11-03 18:00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c3a9e5b7d1f2"
down_revision: str | None = "b7e2d4f1a9c0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chatmute",
        sa.Column(
            "peer_id", sa.BigInteger(), autoincrement=False, nullable=False
        ),
        sa.Column("until", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("peer_id"),
    )


def downgrade() -> None:
    op.drop_table("chatmute")
