import asyncio

from telethon import TelegramClient, events
from telethon.errors import RPCError

from src.config import cfg
from src.core.logger import get_struct_logger
from src.userbot.services.chat_tasks import ChatTaskRegistry
from src.userbot.utils import parse_duration

log = get_struct_logger()


class ChatActionService:
	"""Фейковые «печатает…», «записывает голосовое…» и т.п.: команда сразу
	удаляется, у собеседника висит действие, а сообщения так и нет."""

	# Команда → действие Telethon (что увидит собеседник).
	ACTIONS = {
		"typing": "typing",  # печатает…
		"voice": "record-voice",  # записывает голосовое…
		"round": "record-round",  # записывает видеосообщение…
		"video": "record-video",  # записывает видео…
		"file": "file",  # отправляет файл…
		"photo": "photo",  # отправляет фото…
		"sticker": "sticker",  # выбирает стикер…
	}

	def __init__(self, tasks: ChatTaskRegistry) -> None:
		self.tasks = tasks
		self.settings = cfg.userbot_commands

	async def fake_action(self, event: events.NewMessage.Event) -> None:
		action = self.ACTIONS[event.pattern_match.group(1).lower()]
		raw_duration = event.pattern_match.group(2)
		if raw_duration is None:
			seconds = self.settings.chat_action_default_sec
		else:
			duration = parse_duration(raw_duration)
			if duration is None:
				return  # опечатка — сообщение остаётся как есть
			seconds = min(
				duration.total_seconds(),
				self.settings.chat_action_max_min * 60,
			)
		await self._delete(event)
		log.info("chat_action.started", action=action, seconds=seconds)
		await self.tasks.run(
			event.chat_id,
			self._hold(event.client, event.chat_id, action, seconds),
		)

	async def stop(self, event: events.NewMessage.Event) -> None:
		await self._delete(event)
		if self.tasks.cancel(event.chat_id):
			log.info("chat_action.stopped", chat_id=event.chat_id)

	@staticmethod
	async def _hold(
		client: TelegramClient, chat_id: int, action: str, seconds: float
	) -> None:
		# client.action сам переотправляет действие каждые ~4 с (иначе оно
		# гаснет у собеседника) и шлёт cancel при выходе — в т.ч. по !stop.
		try:
			async with client.action(chat_id, action):
				await asyncio.sleep(seconds)
		except RPCError as e:
			# Например, в канале или чате, где писать нельзя, — действие
			# просто не покажется, это не повод ронять обработчик.
			log.warning("chat_action.failed", action=action, error=e.message)

	@staticmethod
	async def _delete(event: events.NewMessage.Event) -> None:
		try:
			await event.delete()
		except RPCError as e:
			log.warning("chat_action.delete_failed", error=e.message)
