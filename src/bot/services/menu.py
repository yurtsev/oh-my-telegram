from contextlib import suppress

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (
	BotCommand,
	BotCommandScopeChat,
	CallbackQuery,
	InlineKeyboardMarkup,
	Message,
)

from src.bot.keyboards import MenuKeyboards
from src.bot.texts import MenuText
from src.config import cfg
from src.core.logger import get_struct_logger

log = get_struct_logger()


class MenuBotService:
	def __init__(self, bot: Bot) -> None:
		self.bot = bot

	async def setup_commands(self) -> None:
		"""Список команд в кнопке «Меню» Telegram. Только для чата
		владельца: посторонним бот не должен даже подсказывать команды."""
		try:
			await self.bot.set_my_commands(
				[
					BotCommand(command=command, description=description)
					for command, description in MenuText.commands().items()
				],
				scope=BotCommandScopeChat(chat_id=cfg.bot.owner_id),
			)
		except TelegramBadRequest as e:
			# Владелец ещё не писал боту — чата нет. Повторим на /start.
			log.warning("menu.commands_setup_skipped", error=e.message)
			return
		log.info("menu.commands_set")

	async def send_menu(self, message: Message) -> None:
		await message.answer(
			MenuText.main(), reply_markup=MenuKeyboards.main_menu_kb()
		)

	async def show_menu(self, call: CallbackQuery) -> None:
		await self._edit(call, MenuText.main(), MenuKeyboards.main_menu_kb())
		await call.answer()

	async def send_help(self, message: Message) -> None:
		await message.answer(
			MenuText.help(), reply_markup=MenuKeyboards.help_kb()
		)

	async def show_help(self, call: CallbackQuery) -> None:
		await self._edit(call, MenuText.help(), MenuKeyboards.help_kb())
		await call.answer()

	@staticmethod
	async def _edit(
		call: CallbackQuery, text: str, kb: InlineKeyboardMarkup
	) -> None:
		if not isinstance(call.message, Message):
			return
		with suppress(TelegramBadRequest):
			await call.message.edit_text(text, reply_markup=kb)
