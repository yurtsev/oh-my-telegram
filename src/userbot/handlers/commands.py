import re

from telethon import TelegramClient, events

from src.userbot.services.commands import ChatCommandService
from src.userbot.utils import is_dialog_with_person


class UserbotCommandHandlers:
	"""Аналог aiogram-роутера для Telethon: какие события аккаунта ловим и
	в какой метод сервиса отдаём. Клиент аккаунта появляется динамически
	(старт с сохранённой сессией или вход через бота), поэтому обработчики
	вешаются через `attach` на каждый новый клиент."""

	def __init__(self, commands: ChatCommandService) -> None:
		self.commands = commands

	async def attach(self, client: TelegramClient) -> None:
		# outgoing=True ловит и сообщения, отправленные с телефона/десктопа,
		# а не только из этого процесса.
		client.add_event_handler(
			self.commands.mute,
			events.NewMessage(
				outgoing=True,
				pattern=re.compile(
					r"^!mute\s+(\d+\s*[a-zа-яё]+)$", re.IGNORECASE
				),
				func=is_dialog_with_person,
			),
		)
		client.add_event_handler(
			self.commands.unmute,
			events.NewMessage(
				outgoing=True,
				pattern=re.compile(r"^!unmute$", re.IGNORECASE),
				func=is_dialog_with_person,
			),
		)
		client.add_event_handler(
			self.commands.spam,
			events.NewMessage(
				outgoing=True,
				pattern=re.compile(
					r"^!spam\s+(\d+)\s+(.+)$", re.IGNORECASE | re.DOTALL
				),
				# Спам — где угодно; мьют выше/ниже — только личка.
			),
		)
		client.add_event_handler(
			self.commands.on_incoming_private,
			events.NewMessage(incoming=True, func=is_dialog_with_person),
		)
