"""emoji rotation

Revision ID: a1f0c3d9e2b4
Revises:
Create Date: 2026-11-02 23:59:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1f0c3d9e2b4"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "emoji",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("custom_emoji_id", sa.BigInteger(), nullable=False),
        sa.Column("alt", sa.String(length=32), nullable=False),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("custom_emoji_id"),
    )
    op.create_table(
        "emojirotation",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("interval_min", sa.Integer(), nullable=False),
        sa.Column("current_emoji_id", sa.Integer(), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "next_change_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.ForeignKeyConstraint(
            ["current_emoji_id"], ["emoji.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("emojirotation")
    op.drop_table("emoji")
