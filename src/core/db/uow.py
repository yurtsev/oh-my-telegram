from contextlib import AbstractAsyncContextManager
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.repositories import (
	ChatMuteRepo,
	EmojiRepo,
	EmojiRotationRepo,
	UserbotSessionRepo,
)


class UnitOfWork:
	def __init__(self, session: AsyncSession) -> None:
		self.session = session
		self.emojis = EmojiRepo(self.session)
		self.emoji_rotation = EmojiRotationRepo(self.session)
		self.userbot_session = UserbotSessionRepo(self.session)
		self.chat_mutes = ChatMuteRepo(self.session)

	async def commit(self) -> None:
		await self.session.commit()

	async def rollback(self) -> None:
		await self.session.rollback()

	async def flush(self) -> None:
		await self.session.flush()


class UowFactory(Protocol):
	def __call__(self) -> AbstractAsyncContextManager[UnitOfWork]: ...
