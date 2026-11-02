"""emoji playlist: position instead of history

Revision ID: d4b8f6c2e0a1
Revises: c3a9e5b7d1f2
Create Date: 2026-11-03 22:00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d4b8f6c2e0a1"
down_revision: str | None = "c3a9e5b7d1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "emoji",
        sa.Column(
            "position",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    # Уже добавленные эмодзи встают в дорожку в порядке добавления.
    op.execute(
        "UPDATE emoji SET position = ordered.rn "
        "FROM (SELECT id, row_number() OVER (ORDER BY id) - 1 AS rn "
        "FROM emoji) AS ordered WHERE emoji.id = ordered.id"
    )
    op.drop_column("emojirotation", "history_pos")
    op.drop_column("emojirotation", "history")


def downgrade() -> None:
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
    op.drop_column("emoji", "position")
