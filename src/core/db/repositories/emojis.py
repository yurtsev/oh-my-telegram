from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.models import Emoji


class EmojiRepo:
	"""Пул эмодзи как закольцованная дорожка: порядок — по `position`
	(при равных — по `id`)."""

	ORDER = (Emoji.position, Emoji.id)

	def __init__(self, session: AsyncSession):
		self.session = session

	async def get(self, emoji_id: int) -> Emoji | None:
		return await self.session.get(Emoji, emoji_id)

	async def list_all(self) -> list[Emoji]:
		result = await self.session.execute(
			select(Emoji).order_by(*self.ORDER)
		)
		return list(result.scalars().all())

	async def count(self) -> int:
		result = await self.session.execute(select(func.count(Emoji.id)))
		return result.scalar_one()

	async def add_many(self, items: dict[int, str]) -> int:
		"""Добавляет эмодзи `{custom_emoji_id: alt}` в конец дорожки в том же
		порядке, уже существующие пропускает. Возвращает число добавленных."""
		if not items:
			return 0
		start = (
			await self.session.execute(select(func.max(Emoji.position)))
		).scalar_one()
		start = -1 if start is None else start
		stmt = (
			insert(Emoji)
			.values(
				[
					{
						"custom_emoji_id": emoji_id,
						"alt": alt,
						"position": start + i,
					}
					for i, (emoji_id, alt) in enumerate(items.items(), start=1)
				]
			)
			.on_conflict_do_nothing(index_elements=[Emoji.custom_emoji_id])
			.returning(Emoji.id)
		)
		result = await self.session.execute(stmt)
		return len(result.all())

	async def delete(self, emoji_id: int) -> bool:
		result = await self.session.execute(
			delete(Emoji).where(Emoji.id == emoji_id)
		)
		return result.rowcount > 0

	async def after(self, emoji: Emoji) -> Emoji | None:
		"""Следующий трек после `emoji` (без перехода на начало)."""
		stmt = (
			select(Emoji)
			.where(
				(Emoji.position > emoji.position)
				| ((Emoji.position == emoji.position) & (Emoji.id > emoji.id))
			)
			.order_by(*self.ORDER)
			.limit(1)
		)
		return (await self.session.execute(stmt)).scalar_one_or_none()

	async def before(self, emoji: Emoji) -> Emoji | None:
		"""Предыдущий трек перед `emoji` (без перехода в конец)."""
		stmt = (
			select(Emoji)
			.where(
				(Emoji.position < emoji.position)
				| ((Emoji.position == emoji.position) & (Emoji.id < emoji.id))
			)
			.order_by(Emoji.position.desc(), Emoji.id.desc())
			.limit(1)
		)
		return (await self.session.execute(stmt)).scalar_one_or_none()

	async def first(self) -> Emoji | None:
		stmt = select(Emoji).order_by(*self.ORDER).limit(1)
		return (await self.session.execute(stmt)).scalar_one_or_none()

	async def last(self) -> Emoji | None:
		stmt = (
			select(Emoji)
			.order_by(Emoji.position.desc(), Emoji.id.desc())
			.limit(1)
		)
		return (await self.session.execute(stmt)).scalar_one_or_none()

	async def reorder(self, emoji_ids: list[int]) -> None:
		"""Переписывает дорожку: `emoji_ids[0]` становится первым и т.д."""
		if not emoji_ids:
			return
		await self.session.execute(
			update(Emoji),
			[
				{"id": emoji_id, "position": position}
				for position, emoji_id in enumerate(emoji_ids)
			],
		)
