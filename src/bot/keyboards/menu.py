from enum import StrEnum

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class MenuSection(StrEnum):
	main = "main"
	emoji_status = "emoji_status"
	account = "account"
	help = "help"


class MenuData(CallbackData, prefix="menu"):
	section: MenuSection


class MenuKeyboards:
	@staticmethod
	def main_menu_kb() -> InlineKeyboardMarkup:
		ib = InlineKeyboardBuilder()
		ib.button(
			text="🎭 Эмодзи-статус",
			callback_data=MenuData(section=MenuSection.emoji_status),
		)
		ib.button(
			text="👤 Аккаунт",
			callback_data=MenuData(section=MenuSection.account),
		)
		ib.button(
			text="❓ Помощь",
			callback_data=MenuData(section=MenuSection.help),
		)
		return ib.adjust(1).as_markup()

	@staticmethod
	def help_kb() -> InlineKeyboardMarkup:
		ib = InlineKeyboardBuilder()
		ib.button(
			text="◀️ Меню",
			callback_data=MenuData(section=MenuSection.main),
		)
		return ib.as_markup()
