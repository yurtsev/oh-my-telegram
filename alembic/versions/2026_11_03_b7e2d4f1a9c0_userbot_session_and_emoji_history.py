"""userbot session and emoji history

Revision ID: b7e2d4f1a9c0
Revises: a1f0c3d9e2b4
Create Date: 2026-11-03 12:00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b7e2d4f1a9c0"
down_revision: str | None = "a1f0c3d9e2b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "userbotsession",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("tg_user_id", sa.BigInteger(), nullable=False),
        sa.Column("encrypted_session", sa.LargeBinary(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column(
        "emojirotation",
        sa.Column(
            "history",
            postgresql.ARRAY(sa.Integer()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
    )
    op.add_column(
        "emojirotation",
        sa.Column(
            "history_pos",
            sa.Integer(),
            server_default=sa.text("-1"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("emojirotation", "history_pos")
    op.drop_column("emojirotation", "history")
    op.drop_table("userbotsession")
