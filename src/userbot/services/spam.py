import asyncio

from telethon import TelegramClient
from telethon.errors import FloodWaitError, RPCError

from src.config import cfg
from src.core.logger import get_struct_logger

log = get_struct_logger()


class SpamService:
	"""`!spam N текст` — отправляет текст N раз в тот же чат."""

	async def spam(
		self, client: TelegramClient, chat_id: int, count: int, text: str
	) -> int:
		"""Возвращает, сколько сообщений реально ушло."""
		settings = cfg.userbot_commands
		count = min(count, settings.spam_max_count)
		sent = 0
		for _ in range(count):
			try:
				# parse_mode=None — текст уходит ровно как написан, без markdown.
				await client.send_message(chat_id, text, parse_mode=None)
			except FloodWaitError as e:
				# Ждать не будем: спам, доставленный через N минут, уже не
				# смешной, а продолжать — риск ограничений аккаунта.
				log.warning("spam.flood_wait", seconds=e.seconds, sent=sent)
				break
			except RPCError as e:
				log.warning("spam.send_failed", error=e.message, sent=sent)
				break
			sent += 1
			await asyncio.sleep(settings.spam_delay_sec)
		log.info("spam.done", chat_id=chat_id, requested=count, sent=sent)
		return sent
