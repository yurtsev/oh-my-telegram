from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.models import ChatMute


class ChatMuteRepo:
	def __init__(self, session: AsyncSession):
		self.session = session

	async def list_active(self, now: datetime) -> list[ChatMute]:
		result = await self.session.execute(
			select(ChatMute).where(ChatMute.until > now)
		)
		return list(result.scalars().all())

	async def upsert(self, peer_id: int, until: datetime) -> None:
		stmt = insert(ChatMute).values(peer_id=peer_id, until=until)
		await self.session.execute(
			stmt.on_conflict_do_update(
				index_elements=[ChatMute.peer_id],
				set_={"until": stmt.excluded.until},
			)
		)

	async def delete(self, peer_id: int) -> None:
		await self.session.execute(
			delete(ChatMute).where(ChatMute.peer_id == peer_id)
		)

	async def delete_expired(self, now: datetime) -> None:
		await self.session.execute(
			delete(ChatMute).where(ChatMute.until <= now)
		)
