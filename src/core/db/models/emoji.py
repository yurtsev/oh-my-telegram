from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.db.base import Base


class Emoji(Base):
	"""Кастомный (премиум) эмодзи — трек в закольцованной дорожке
	эмодзи-статуса."""

	id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
	# document_id кастомного эмодзи в Telegram — именно его ставим в статус.
	custom_emoji_id: Mapped[int] = mapped_column(BigInteger, unique=True)
	# Обычный unicode-эмодзи, к которому привязан кастомный. Боту нельзя
	# отправлять кастомные эмодзи без купленного на Fragment юзернейма,
	# поэтому в интерфейсе пул показывается через alt.
	alt: Mapped[str] = mapped_column(String(32), default="")
	# Место в дорожке. Не уникально и может идти с пропусками (после
	# удалений) — важен только порядок; 🔀 переписывает его целиком.
	position: Mapped[int] = mapped_column(default=0)
	added_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now()
	)
