import re
from collections.abc import Awaitable, Callable
from contextlib import suppress

from aiogram import Bot
from aiogram.enums import MessageEntityType
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from src.bot.keyboards import EmojiStatusKeyboards
from src.bot.states import EmojiStatusState
from src.bot.texts import EmojiStatusText
from src.config import cfg
from src.core.db import Emoji
from src.core.logger import get_struct_logger
from src.exc import (
	EmojiStatusApplyError,
	EmptyEmojiPoolError,
	InvalidRotationIntervalError,
	UserbotNotAuthorizedError,
)
from src.services.emoji_rotation import EmojiRotationService

log = get_struct_logger()

PACK_LINK_RE = re.compile(r"t\.me/addemoji/([A-Za-z0-9_]+)")
INTERVAL_PART_RE = re.compile(r"(\d+)\s*([дdчhмm]?)", re.IGNORECASE)
INTERVAL_UNITS = {
	"": 1,
	"м": 1,
	"m": 1,
	"ч": 60,
	"h": 60,
	"д": 1440,
	"d": 1440,
}


class EmojiStatusBotService:
	"""UI-сценарии раздела «Эмодзи-статус»: рендер экранов и разбор
	пользовательского ввода. Вся логика пула/ротации — в
	`EmojiRotationService`."""

	def __init__(self, rotation: EmojiRotationService, bot: Bot) -> None:
		self.rotation = rotation
		self.bot = bot

	# --- Главный экран ---

	async def send_screen(self, message: Message) -> None:
		text, kb = await self._screen()
		await message.answer(text, reply_markup=kb)

	async def show_screen(self, call: CallbackQuery) -> None:
		text, kb = await self._screen()
		await self._edit(call, text, kb)
		await call.answer()

	async def next_emoji(self, call: CallbackQuery) -> None:
		await self._switch(call, self.rotation.rotate_now)

	async def previous_emoji(self, call: CallbackQuery) -> None:
		await self._switch(call, self.rotation.previous)

	async def delete_current(self, call: CallbackQuery) -> None:
		snapshot = await self.rotation.snapshot()
		if snapshot.current is None:
			await call.answer(EmojiStatusText.no_current(), show_alert=True)
			return
		alert = await self._delete(snapshot.current.id)
		text, kb = await self._screen()
		await self._edit(call, text, kb)
		await call.answer(alert)

	async def toggle(self, call: CallbackQuery) -> None:
		snapshot = await self.rotation.snapshot()
		await self.rotation.set_enabled(not snapshot.enabled)
		await self.show_screen(call)

	# --- Добавление ---

	async def start_add(self, call: CallbackQuery, state: FSMContext) -> None:
		await state.set_state(EmojiStatusState.wait_emojis)
		await self._edit(
			call, EmojiStatusText.add_prompt(), EmojiStatusKeyboards.add_kb()
		)
		await call.answer()

	async def add_from_message(self, message: Message) -> None:
		items, failed_packs = await self.extract_custom_emojis(message)
		if not items and not failed_packs:
			await message.answer(
				EmojiStatusText.nothing_found(),
				reply_markup=EmojiStatusKeyboards.add_kb(),
			)
			return
		added, total = await self.rotation.add_emojis(items)
		await message.answer(
			EmojiStatusText.added(added, total, failed_packs),
			reply_markup=EmojiStatusKeyboards.add_kb(),
		)

	async def finish_add(self, call: CallbackQuery, state: FSMContext) -> None:
		await state.clear()
		await self.show_screen(call)

	async def extract_custom_emojis(
		self, message: Message
	) -> tuple[dict[int, str], list[str]]:
		"""Премиум-эмодзи из сообщения + целиком паки по ссылкам
		`t.me/addemoji/<name>`. Возвращает ({custom_emoji_id: alt},
		[имена ненайденных паков])."""
		text = message.text or message.caption or ""
		entities = message.entities or message.caption_entities or []
		items = {
			int(entity.custom_emoji_id): entity.extract_from(text)
			for entity in entities
			if entity.type == MessageEntityType.CUSTOM_EMOJI
			and entity.custom_emoji_id
		}

		failed_packs: list[str] = []
		for pack_name in dict.fromkeys(PACK_LINK_RE.findall(text)):
			try:
				sticker_set = await self.bot.get_sticker_set(pack_name)
			except TelegramBadRequest as e:
				log.warning(
					"emoji_pool.pack_not_found",
					pack=pack_name,
					error=e.message,
				)
				failed_packs.append(pack_name)
				continue
			for sticker in sticker_set.stickers:
				if sticker.custom_emoji_id:
					items[int(sticker.custom_emoji_id)] = sticker.emoji or ""
		return items, failed_packs

	# --- Пул ---

	async def show_pool(self, call: CallbackQuery, page: int) -> None:
		await self._render_pool(call, page)
		await call.answer()

	async def delete_from_pool(
		self, call: CallbackQuery, emoji_id: int, page: int
	) -> None:
		alert = await self._delete(emoji_id)
		await self._render_pool(call, page)
		await call.answer(alert)

	async def shuffle(self, call: CallbackQuery) -> None:
		await self.rotation.shuffle()
		# Текущий после перемешивания первый — показываем с начала.
		await self._render_pool(call, page=0)
		await call.answer(EmojiStatusText.shuffled())

	async def _render_pool(self, call: CallbackQuery, page: int) -> None:
		snapshot = await self.rotation.snapshot()
		await self._edit(
			call,
			EmojiStatusText.pool_screen(len(snapshot.pool)),
			EmojiStatusKeyboards.pool_kb(
				snapshot.pool,
				page,
				snapshot.current.id if snapshot.current else None,
			),
		)

	# --- Интервал ---

	async def show_intervals(self, call: CallbackQuery) -> None:
		snapshot = await self.rotation.snapshot()
		await self._edit(
			call,
			EmojiStatusText.interval_prompt(snapshot.interval_min),
			EmojiStatusKeyboards.intervals_kb(snapshot.interval_min),
		)
		await call.answer()

	async def set_interval(self, call: CallbackQuery, minutes: int) -> None:
		await self.rotation.set_interval(minutes)
		text, kb = await self._screen()
		await self._edit(call, text, kb)
		await call.answer(EmojiStatusText.interval_set(minutes))

	async def start_custom_interval(
		self, call: CallbackQuery, state: FSMContext
	) -> None:
		await state.set_state(EmojiStatusState.wait_interval)
		await self._edit(
			call,
			EmojiStatusText.custom_interval_prompt(
				cfg.emoji_rotation.min_interval_min,
				cfg.emoji_rotation.max_interval_min,
			),
			EmojiStatusKeyboards.back_to_screen_kb(),
		)
		await call.answer()

	async def custom_interval_from_message(
		self, message: Message, state: FSMContext
	) -> None:
		minutes = self.parse_interval(message.text or "")
		if minutes is not None:
			with suppress(InvalidRotationIntervalError):
				await self.rotation.set_interval(minutes)
				await state.clear()
				await message.answer(EmojiStatusText.interval_set(minutes))
				await self.send_screen(message)
				return
		await message.answer(
			EmojiStatusText.interval_invalid(
				cfg.emoji_rotation.min_interval_min,
				cfg.emoji_rotation.max_interval_min,
			),
			reply_markup=EmojiStatusKeyboards.back_to_screen_kb(),
		)

	@staticmethod
	def parse_interval(raw: str) -> int | None:
		"""«90» / «90м» → 90, «2ч» → 120, «1д» → 1440, «1ч30м» → 90."""
		cleaned = raw.strip().lower().replace(" ", "")
		parts = INTERVAL_PART_RE.findall(cleaned)
		# Всё, что не разобралось регуляркой (буквы-мусор), — невалидно.
		if not parts or "".join(n + u for n, u in parts) != cleaned:
			return None
		return sum(int(n) * INTERVAL_UNITS[u] for n, u in parts)

	# --- Внутреннее ---

	async def _screen(self) -> tuple[str, InlineKeyboardMarkup]:
		snapshot = await self.rotation.snapshot()
		return EmojiStatusText.screen(
			snapshot
		), EmojiStatusKeyboards.screen_kb(
			enabled=snapshot.enabled, has_current=snapshot.current is not None
		)

	async def _switch(
		self, call: CallbackQuery, switch: Callable[[], Awaitable[Emoji]]
	) -> None:
		"""Общая обвязка ⏮/⏭: смена + перерисовка + всплывашка."""
		try:
			emoji = await switch()
		except EmptyEmojiPoolError:
			await call.answer(EmojiStatusText.empty_pool(), show_alert=True)
			return
		except UserbotNotAuthorizedError:
			await call.answer(
				EmojiStatusText.account_not_connected(), show_alert=True
			)
			return
		except EmojiStatusApplyError as e:
			await call.answer(
				EmojiStatusText.apply_failed(e.reason), show_alert=True
			)
			return
		text, kb = await self._screen()
		await self._edit(call, text, kb)
		await call.answer(EmojiStatusText.rotated(emoji.alt))

	async def _delete(self, emoji_id: int) -> str:
		"""Удаляет эмодзи и возвращает текст всплывашки о результате."""
		try:
			new_current = await self.rotation.delete_emoji(emoji_id)
		except UserbotNotAuthorizedError:
			return EmojiStatusText.deleted_not_connected()
		except EmojiStatusApplyError as e:
			return EmojiStatusText.apply_failed(e.reason)
		return EmojiStatusText.deleted(
			new_current.alt if new_current is not None else None
		)

	@staticmethod
	async def _edit(
		call: CallbackQuery, text: str, kb: InlineKeyboardMarkup
	) -> None:
		if not isinstance(call.message, Message):
			return
		# Повторный рендер того же экрана — Telegram отвечает
		# «message is not modified», это не ошибка.
		with suppress(TelegramBadRequest):
			await call.message.edit_text(text, reply_markup=kb)
