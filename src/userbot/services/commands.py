from telethon import events
from telethon.errors import RPCError

from src.core.logger import get_struct_logger
from src.userbot.services.mute import ChatMuteService
from src.userbot.services.spam import SpamService
from src.userbot.texts.commands import CommandText
from src.userbot.utils import parse_duration

log = get_struct_logger()


class ChatCommandService:
	"""Команды, которые владелец пишет прямо в личке с собеседником:
	`!mute 10min`, `!unmute`, `!spam 5 текст`. Разбор и реакция на команду —
	здесь; что именно срабатывает и где (только личка) — в
	`userbot/handlers/commands.py`."""

	def __init__(self, mutes: ChatMuteService, spam: SpamService) -> None:
		self.mutes = mutes
		self.spam_service = spam

	async def mute(self, event: events.NewMessage.Event) -> None:
		duration = parse_duration(event.pattern_match.group(1))
		if duration is None:
			# Опечатка — команда остаётся обычным сообщением, собеседник не
			# видит никаких «ошибок бота».
			return
		await self.mutes.mute(event.chat_id, duration)
		await self._edit(event, CommandText.muted())

	async def unmute(self, event: events.NewMessage.Event) -> None:
		await self.mutes.unmute(event.chat_id)
		await self._edit(event, CommandText.unmuted())

	async def spam(self, event: events.NewMessage.Event) -> None:
		count = int(event.pattern_match.group(1))
		text = event.pattern_match.group(2)
		if count == 0:
			return
		await self._delete(event)
		await self.spam_service.spam(event.client, event.chat_id, count, text)

	async def on_incoming_private(
		self, event: events.NewMessage.Event
	) -> None:
		if self.mutes.is_muted(event.chat_id):
			await self._delete(event)

	@staticmethod
	async def _edit(event: events.NewMessage.Event, text: str) -> None:
		try:
			await event.edit(text)
		except RPCError as e:
			log.warning("commands.edit_failed", error=e.message)

	@staticmethod
	async def _delete(event: events.NewMessage.Event) -> None:
		try:
			# В личке revoke=True (по умолчанию) удаляет у обоих.
			await event.delete()
		except RPCError as e:
			log.warning("commands.delete_failed", error=e.message)
