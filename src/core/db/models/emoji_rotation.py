from datetime import datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.db.base import Base
from src.core.db.models.emoji import Emoji


class EmojiRotation(Base):
	"""Настройки и состояние ротации эмодзи-статуса. Аккаунт один —
	строка в таблице тоже одна (id = SINGLETON_ID)."""

	SINGLETON_ID = 1

	id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
	enabled: Mapped[bool] = mapped_column(default=True)
	interval_min: Mapped[int]
	current_emoji_id: Mapped[int | None] = mapped_column(
		ForeignKey("emoji.id", ondelete="SET NULL"), nullable=True
	)
	changed_at: Mapped[datetime | None] = mapped_column(
		DateTime(timezone=True), nullable=True
	)
	next_change_at: Mapped[datetime | None] = mapped_column(
		DateTime(timezone=True), nullable=True
	)

	current_emoji: Mapped[Emoji | None] = relationship(lazy="joined")
