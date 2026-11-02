from enum import StrEnum

from aiogram.filters.callback_data import CallbackData
from aiogram.types import (
	InlineKeyboardMarkup,
	ReplyKeyboardMarkup,
	ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from src.bot.keyboards.menu import MenuData, MenuSection

CANCEL_LOGIN_LABEL = "✖️ Отмена"
LOGIN_CODE_MAX_LEN = 6


class AccountAction(StrEnum):
	screen = "screen"
	connect = "connect"
	logout = "logout"
	logout_confirm = "logout_ok"
	digit = "digit"
	backspace = "bksp"
	submit_code = "submit"
	cancel = "cancel"


class AccountData(CallbackData, prefix="acc"):
	action: AccountAction
	digit: int = 0


class AccountKeyboards:
	@staticmethod
	def screen_kb(*, connected: bool) -> InlineKeyboardMarkup:
		ib = InlineKeyboardBuilder()
		if connected:
			ib.button(
				text="🔄 Переподключить",
				callback_data=AccountData(action=AccountAction.connect),
			)
			ib.button(
				text="🚪 Выйти и отозвать сессию",
				callback_data=AccountData(action=AccountAction.logout),
			)
		else:
			ib.button(
				text="🔌 Подключить аккаунт",
				callback_data=AccountData(action=AccountAction.connect),
			)
		ib.button(
			text="◀️ Меню",
			callback_data=MenuData(section=MenuSection.main),
		)
		return ib.adjust(1).as_markup()

	@staticmethod
	def contact_kb() -> ReplyKeyboardMarkup:
		rb = ReplyKeyboardBuilder()
		rb.button(text="📱 Поделиться контактом", request_contact=True)
		rb.button(text=CANCEL_LOGIN_LABEL)
		return rb.adjust(1).as_markup(
			resize_keyboard=True, one_time_keyboard=True
		)

	@staticmethod
	def remove_kb() -> ReplyKeyboardRemove:
		return ReplyKeyboardRemove()

	@staticmethod
	def code_kb() -> InlineKeyboardMarkup:
		# Код набирается кнопками: нажатия — это callback, а не сообщение,
		# поэтому Telegram не видит код в переписке и не аннулирует его.
		ib = InlineKeyboardBuilder()
		for digit in (1, 2, 3, 4, 5, 6, 7, 8, 9):
			ib.button(
				text=str(digit),
				callback_data=AccountData(
					action=AccountAction.digit, digit=digit
				),
			)
		ib.button(
			text="⌫",
			callback_data=AccountData(action=AccountAction.backspace),
		)
		ib.button(
			text="0",
			callback_data=AccountData(action=AccountAction.digit, digit=0),
		)
		ib.button(
			text="✅",
			callback_data=AccountData(action=AccountAction.submit_code),
		)
		ib.button(
			text=CANCEL_LOGIN_LABEL,
			callback_data=AccountData(action=AccountAction.cancel),
		)
		return ib.adjust(3, 3, 3, 3, 1).as_markup()

	@staticmethod
	def cancel_kb() -> InlineKeyboardMarkup:
		ib = InlineKeyboardBuilder()
		ib.button(
			text=CANCEL_LOGIN_LABEL,
			callback_data=AccountData(action=AccountAction.cancel),
		)
		return ib.as_markup()

	@staticmethod
	def logout_confirm_kb() -> InlineKeyboardMarkup:
		ib = InlineKeyboardBuilder()
		ib.button(
			text="🚪 Да, выйти",
			callback_data=AccountData(action=AccountAction.logout_confirm),
		)
		ib.button(
			text="↩️ Назад",
			callback_data=AccountData(action=AccountAction.screen),
		)
		return ib.adjust(2).as_markup()
