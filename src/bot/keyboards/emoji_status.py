from enum import StrEnum

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.keyboards.menu import MenuData, MenuSection
from src.bot.utils import format_interval
from src.core.db import Emoji

POOL_PAGE_SIZE = 20


class EmojiStatusAction(StrEnum):
	screen = "screen"
	previous = "prev"
	next = "next"
	delete_current = "del_cur"
	toggle = "toggle"
	add = "add"
	add_done = "add_done"
	pool = "pool"
	shuffle = "shuffle"
	delete = "del"
	intervals = "intervals"
	set_interval = "set_int"
	custom_interval = "custom_int"


class EmojiStatusData(CallbackData, prefix="es"):
	action: EmojiStatusAction
	# id эмодзи для delete, минуты для set_interval, страница для pool.
	value: int = 0
	page: int = 0


class EmojiStatusKeyboards:
	@staticmethod
	def screen_kb(*, enabled: bool, has_current: bool) -> InlineKeyboardMarkup:
		# Верхний ряд — как в плеере: назад / пауза / вперёд.
		ib = InlineKeyboardBuilder()
		ib.button(
			text="⏮",
			callback_data=EmojiStatusData(action=EmojiStatusAction.previous),
		)
		ib.button(
			text="⏸" if enabled else "▶️",
			callback_data=EmojiStatusData(action=EmojiStatusAction.toggle),
		)
		ib.button(
			text="⏭",
			callback_data=EmojiStatusData(action=EmojiStatusAction.next),
		)
		if has_current:
			ib.button(
				text="🗑 Удалить текущий",
				callback_data=EmojiStatusData(
					action=EmojiStatusAction.delete_current
				),
			)
		ib.button(
			text="➕ Добавить",
			callback_data=EmojiStatusData(action=EmojiStatusAction.add),
		)
		ib.button(
			text="📋 Пул",
			callback_data=EmojiStatusData(action=EmojiStatusAction.pool),
		)
		ib.button(
			text="⏱ Интервал",
			callback_data=EmojiStatusData(action=EmojiStatusAction.intervals),
		)
		ib.button(
			text="◀️ Меню",
			callback_data=MenuData(section=MenuSection.main),
		)
		layout = (3, 1, 2, 2) if has_current else (3, 2, 2)
		return ib.adjust(*layout).as_markup()

	@staticmethod
	def add_kb() -> InlineKeyboardMarkup:
		ib = InlineKeyboardBuilder()
		ib.button(
			text="✅ Готово",
			callback_data=EmojiStatusData(action=EmojiStatusAction.add_done),
		)
		return ib.as_markup()

	@staticmethod
	def pool_kb(
		pool: list[Emoji], page: int, current_id: int | None
	) -> InlineKeyboardMarkup:
		"""Дорожка по порядку; ▶️ — то, что сейчас в статусе. Нажатие на
		эмодзи удаляет его."""
		pages = max(1, -(-len(pool) // POOL_PAGE_SIZE))
		page = min(max(page, 0), pages - 1)
		start = page * POOL_PAGE_SIZE
		chunk = pool[start : start + POOL_PAGE_SIZE]

		ib = InlineKeyboardBuilder()
		for number, emoji in enumerate(chunk, start=start + 1):
			playing = "▶️" if emoji.id == current_id else ""
			ib.button(
				text=f"{playing}{emoji.alt or '❔'} {number}",
				callback_data=EmojiStatusData(
					action=EmojiStatusAction.delete, value=emoji.id, page=page
				),
			)
		ib.adjust(5)

		nav = InlineKeyboardBuilder()
		if len(pool) > 1:
			nav.button(
				text="🔀 Перемешать",
				callback_data=EmojiStatusData(
					action=EmojiStatusAction.shuffle
				),
			)
		if page > 0:
			nav.button(
				text="◀️",
				callback_data=EmojiStatusData(
					action=EmojiStatusAction.pool, page=page - 1
				),
			)
		if page < pages - 1:
			nav.button(
				text="▶️",
				callback_data=EmojiStatusData(
					action=EmojiStatusAction.pool, page=page + 1
				),
			)
		nav.button(
			text="↩️ Назад",
			callback_data=EmojiStatusData(action=EmojiStatusAction.screen),
		)
		ib.attach(nav.adjust(1, 3) if len(pool) > 1 else nav.adjust(3))
		return ib.as_markup()

	@staticmethod
	def intervals_kb(current_min: int) -> InlineKeyboardMarkup:
		ib = InlineKeyboardBuilder()
		for minutes in (15, 30, 60, 180, 360, 720, 1440, 2880):
			mark = "• " if minutes == current_min else ""
			ib.button(
				text=f"{mark}{format_interval(minutes)}",
				callback_data=EmojiStatusData(
					action=EmojiStatusAction.set_interval, value=minutes
				),
			)
		ib.button(
			text="✏️ Своё",
			callback_data=EmojiStatusData(
				action=EmojiStatusAction.custom_interval
			),
		)
		ib.button(
			text="↩️ Назад",
			callback_data=EmojiStatusData(action=EmojiStatusAction.screen),
		)
		return ib.adjust(4, 4, 2).as_markup()

	@staticmethod
	def back_to_screen_kb() -> InlineKeyboardMarkup:
		ib = InlineKeyboardBuilder()
		ib.button(
			text="↩️ Назад",
			callback_data=EmojiStatusData(action=EmojiStatusAction.screen),
		)
		return ib.as_markup()
