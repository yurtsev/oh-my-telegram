import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from src.config import cfg
from src.core.db import Emoji, EmojiRotation
from src.core.db.uow import UnitOfWork, UowFactory
from src.core.logger import get_struct_logger
from src.core.scheduling import Wakeup
from src.exc import (
	EmojiStatusApplyError,
	EmptyEmojiPoolError,
	InvalidRotationIntervalError,
)
from src.userbot.services.emoji_status import AccountEmojiStatusService

log = get_struct_logger()


@dataclass(frozen=True, slots=True)
class RotationSnapshot:
	enabled: bool
	interval_min: int
	current: Emoji | None
	changed_at: datetime | None
	next_change_at: datetime | None
	pool: list[Emoji]  # в порядке дорожки

	@property
	def current_index(self) -> int | None:
		"""Номер текущего трека в дорожке (с 1) — для «3/12»."""
		if self.current is None:
			return None
		ids = [emoji.id for emoji in self.pool]
		return (
			ids.index(self.current.id) + 1 if self.current.id in ids else None
		)


class EmojiRotationService:
	"""Пул эмодзи и их ротация в статусе аккаунта. Один источник правды и
	для кнопок бота, и для фонового цикла (`runtime/emoji_rotation.py`).

	Работает как плеер с закольцованным плейлистом: пул — дорожка в
	порядке добавления, ⏭ и смена по таймеру идут по ней вперёд, ⏮ —
	назад, после последнего снова первый. 🔀 перемешивает дорожку.
	"""

	def __init__(
		self,
		uow_factory: UowFactory,
		account_status: AccountEmojiStatusService,
		wakeup: Wakeup,
	) -> None:
		self.uow_factory = uow_factory
		self.account_status = account_status
		# Будит планировщик после любого изменения расписания — иначе он
		# проспал бы до старого дедлайна (`runtime/emoji_rotation.py`).
		self.wakeup = wakeup
		self.settings = cfg.emoji_rotation

	async def snapshot(self) -> RotationSnapshot:
		async with self.uow_factory() as uow:
			rotation = await self._lock_rotation(uow)
			pool = await uow.emojis.list_all()
			await uow.commit()
		return RotationSnapshot(
			enabled=rotation.enabled,
			interval_min=rotation.interval_min,
			current=rotation.current_emoji,
			changed_at=rotation.changed_at,
			next_change_at=rotation.next_change_at,
			pool=pool,
		)

	async def next_due_at(self) -> datetime | None:
		"""Когда планировщику в следующий раз звать `rotate_if_due`.
		None — менять нечего (пауза или пустой пул), спать до `notify()`."""
		async with self.uow_factory() as uow:
			rotation = await self._lock_rotation(uow)
			pool_size = await uow.emojis.count()
			await uow.commit()
		if not rotation.enabled or pool_size == 0:
			return None
		return rotation.next_change_at or datetime.now(UTC)

	async def rotate_now(self) -> Emoji:
		"""Кнопка ⏭."""
		return await self._switch(self._following)

	async def previous(self) -> Emoji:
		"""Кнопка ⏮."""
		return await self._switch(self._preceding)

	async def shuffle(self) -> None:
		"""Кнопка 🔀: как в музыке — текущий трек продолжает играть и
		становится первым, остальные встают после него в случайном
		порядке."""
		async with self.uow_factory() as uow:
			rotation = await self._lock_rotation(uow)
			ids = [emoji.id for emoji in await uow.emojis.list_all()]
			random.shuffle(ids)
			if rotation.current_emoji_id in ids:
				ids.remove(rotation.current_emoji_id)
				ids.insert(0, rotation.current_emoji_id)
			await uow.emojis.reorder(ids)
			await uow.commit()
		log.info("emoji_pool.shuffled", size=len(ids))

	async def rotate_if_due(self) -> Emoji | None:
		async with self.uow_factory() as uow:
			rotation = await self._lock_rotation(uow)
			now = datetime.now(UTC)
			is_due = rotation.next_change_at is None or (
				rotation.next_change_at <= now
			)
			if not rotation.enabled or not is_due:
				await uow.commit()
				return None
			emoji = await self._following(uow, rotation)
			if emoji is None:
				# Пул пуст — next_change_at остаётся «просроченным»;
				# add_emojis разбудит планировщик, и тот сразу поставит
				# статус.
				await uow.commit()
				return None
			try:
				await self._apply(rotation, emoji)
			except EmojiStatusApplyError as e:
				retry_sec = max(
					self.settings.retry_delay_min * 60,
					e.retry_after_sec or 0,
				)
				rotation.next_change_at = now + timedelta(seconds=retry_sec)
				await uow.commit()
				raise
			await uow.commit()
		return emoji

	async def set_interval(self, minutes: int) -> None:
		if not (
			self.settings.min_interval_min
			<= minutes
			<= self.settings.max_interval_min
		):
			raise InvalidRotationIntervalError(
				minutes,
				self.settings.min_interval_min,
				self.settings.max_interval_min,
			)
		async with self.uow_factory() as uow:
			rotation = await self._lock_rotation(uow)
			rotation.interval_min = minutes
			# Новый интервал отсчитывается от последней смены, а не от
			# «сейчас» — иначе частые правки настройки отодвигали бы смену.
			if rotation.changed_at is not None:
				rotation.next_change_at = rotation.changed_at + timedelta(
					minutes=minutes
				)
			await uow.commit()
		self.wakeup.notify()
		log.info("emoji_rotation.interval_set", minutes=minutes)

	async def set_enabled(self, enabled: bool) -> None:
		async with self.uow_factory() as uow:
			rotation = await self._lock_rotation(uow)
			rotation.enabled = enabled
			await uow.commit()
		self.wakeup.notify()
		log.info("emoji_rotation.enabled_set", enabled=enabled)

	async def add_emojis(self, items: dict[int, str]) -> tuple[int, int]:
		"""Добавляет в конец дорожки. Возвращает (добавлено, всего в пуле)."""
		async with self.uow_factory() as uow:
			added = await uow.emojis.add_many(items)
			total = await uow.emojis.count()
			await uow.commit()
		self.wakeup.notify()
		log.info("emoji_pool.added", added=added, total=total)
		return added, total

	async def delete_emoji(self, emoji_id: int) -> Emoji | None:
		"""Удаляет эмодзи из дорожки. Если он сейчас стоит в статусе — сразу
		ставит следующий по дорожке (или очищает статус, если пул опустел).
		Возвращает эмодзи, который теперь в статусе."""
		async with self.uow_factory() as uow:
			rotation = await self._lock_rotation(uow)
			current = rotation.current_emoji
			was_current = current is not None and current.id == emoji_id
			successor = (
				await uow.emojis.after(current) if was_current else None
			)
			if was_current:
				rotation.current_emoji = None
				# Если смена ниже упадёт — планировщик подхватит сразу.
				rotation.next_change_at = datetime.now(UTC)
				await uow.flush()
			await uow.emojis.delete(emoji_id)
			await uow.commit()
		self.wakeup.notify()
		log.info("emoji_pool.deleted", emoji_id=emoji_id, current=was_current)

		if not was_current:
			return None
		successor_id = successor.id if successor is not None else None

		async def pick_successor(
			uow: UnitOfWork, _rotation: EmojiRotation
		) -> Emoji | None:
			# Удалили последний трек дорожки — по кругу на первый.
			found = (
				await uow.emojis.get(successor_id) if successor_id else None
			)
			return found or await uow.emojis.first()

		try:
			return await self._switch(pick_successor)
		except EmptyEmojiPoolError:
			await self.account_status.set_status(None)
			return None

	async def _lock_rotation(self, uow: UnitOfWork) -> EmojiRotation:
		return await uow.emoji_rotation.get_for_update(
			self.settings.default_interval_min
		)

	async def _switch(
		self,
		pick: Callable[[UnitOfWork, EmojiRotation], Awaitable[Emoji | None]],
	) -> Emoji:
		async with self.uow_factory() as uow:
			rotation = await self._lock_rotation(uow)
			emoji = await pick(uow, rotation)
			if emoji is None:
				raise EmptyEmojiPoolError
			await self._apply(rotation, emoji)
			await uow.commit()
		self.wakeup.notify()
		return emoji

	@staticmethod
	async def _following(
		uow: UnitOfWork, rotation: EmojiRotation
	) -> Emoji | None:
		# Трек из одного эмодзи — after() пуст, first() вернёт его же:
		# переставляем и сбрасываем таймер.
		current = rotation.current_emoji
		if current is None:
			return await uow.emojis.first()
		return await uow.emojis.after(current) or await uow.emojis.first()

	@staticmethod
	async def _preceding(
		uow: UnitOfWork, rotation: EmojiRotation
	) -> Emoji | None:
		current = rotation.current_emoji
		if current is None:
			return await uow.emojis.last()
		return await uow.emojis.before(current) or await uow.emojis.last()

	async def _apply(self, rotation: EmojiRotation, emoji: Emoji) -> None:
		await self.account_status.set_status(emoji.custom_emoji_id)
		now = datetime.now(UTC)
		rotation.current_emoji = emoji
		rotation.changed_at = now
		rotation.next_change_at = now + timedelta(
			minutes=rotation.interval_min
		)
		log.info(
			"emoji_rotation.rotated",
			emoji_id=emoji.id,
			next_change_at=rotation.next_change_at.isoformat(),
		)
