from datetime import datetime

from sqlalchemy import BigInteger, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.db.base import Base


class ChatMute(Base):
	"""Мьют собеседника в личке (`!mute`): пока не наступил `until`, все
	его новые сообщения удаляются у обоих."""

	peer_id: Mapped[int] = mapped_column(
		BigInteger, primary_key=True, autoincrement=False
	)
	until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now()
	)
