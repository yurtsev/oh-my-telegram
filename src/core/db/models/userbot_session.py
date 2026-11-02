from datetime import datetime

from sqlalchemy import BigInteger, DateTime, LargeBinary, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.db.base import Base


class UserbotSession(Base):
	"""Сессия аккаунта владельца. Хранится только зашифрованной
	(`SessionCipher`); телефон, код и пароль не сохраняются вообще."""

	SINGLETON_ID = 1

	id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
	tg_user_id: Mapped[int] = mapped_column(BigInteger)
	encrypted_session: Mapped[bytes] = mapped_column(LargeBinary)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now()
	)
