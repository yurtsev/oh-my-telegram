from sqlalchemy import delete, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.models import UserbotSession


class UserbotSessionRepo:
	def __init__(self, session: AsyncSession):
		self.session = session

	async def get(self) -> UserbotSession | None:
		return await self.session.get(
			UserbotSession, UserbotSession.SINGLETON_ID
		)

	async def save(self, tg_user_id: int, encrypted_session: bytes) -> None:
		stmt = insert(UserbotSession).values(
			id=UserbotSession.SINGLETON_ID,
			tg_user_id=tg_user_id,
			encrypted_session=encrypted_session,
		)
		await self.session.execute(
			stmt.on_conflict_do_update(
				index_elements=[UserbotSession.id],
				set_={
					"tg_user_id": stmt.excluded.tg_user_id,
					"encrypted_session": stmt.excluded.encrypted_session,
					"created_at": func.now(),
				},
			)
		)

	async def delete(self) -> None:
		await self.session.execute(delete(UserbotSession))
