from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.models import EmojiRotation


class EmojiRotationRepo:
	def __init__(self, session: AsyncSession):
		self.session = session

	async def get_for_update(self, default_interval_min: int) -> EmojiRotation:
		"""Строка настроек под блокировкой — смену может одновременно
		запустить и планировщик, и кнопка в боте. Если строки ещё нет,
		создаётся с дефолтами."""
		await self.session.execute(
			insert(EmojiRotation)
			.values(
				id=EmojiRotation.SINGLETON_ID,
				enabled=True,
				interval_min=default_interval_min,
			)
			.on_conflict_do_nothing(index_elements=[EmojiRotation.id])
		)
		rotation = await self.session.get(
			EmojiRotation,
			EmojiRotation.SINGLETON_ID,
			with_for_update={"of": EmojiRotation},
			populate_existing=True,
		)
		if rotation is None:
			raise RuntimeError("emoji_rotation row must exist after upsert")
		return rotation
