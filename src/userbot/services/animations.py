import asyncio

from telethon import events
from telethon.errors import FloodWaitError, MessageNotModifiedError, RPCError

from src.config import cfg
from src.core.logger import get_struct_logger
from src.userbot.services.chat_tasks import ChatTaskRegistry
from src.userbot.texts.animations import AnimationText

log = get_struct_logger()


class AnimationService:
	"""Анимации сообщений: команда (`!type`, `!🌑`, `!❤️`) редактируется
	покадрово прямо в чате."""

	def __init__(self, tasks: ChatTaskRegistry) -> None:
		self.tasks = tasks
		self.settings = cfg.userbot_commands

	async def typewriter(self, event: events.NewMessage.Event) -> None:
		frames = AnimationText.typewriter(
			event.pattern_match.group(1), self.settings.typewriter_max_frames
		)
		await self._play(event, frames, self.settings.typewriter_delay_sec)

	async def moon(self, event: events.NewMessage.Event) -> None:
		frames = AnimationText.moon_cycle(event.pattern_match.group(1))
		await self._play(event, frames, self.settings.animation_delay_sec)

	async def hearts(self, event: events.NewMessage.Event) -> None:
		await self._play(
			event, AnimationText.hearts(), self.settings.animation_delay_sec
		)

	async def _play(
		self, event: events.NewMessage.Event, frames: list[str], delay: float
	) -> None:
		await self.tasks.run(event.chat_id, self._frames(event, frames, delay))

	@staticmethod
	async def _frames(
		event: events.NewMessage.Event, frames: list[str], delay: float
	) -> None:
		previous = event.raw_text
		for index, frame in enumerate(frames):
			if frame == previous:
				continue
			if index:
				await asyncio.sleep(delay)
			try:
				# parse_mode=None: «*», «_» и «`» в тексте пользователя не
				# должны превращаться в разметку посреди анимации.
				await event.edit(frame, parse_mode=None)
			except MessageNotModifiedError:
				pass
			except FloodWaitError as e:
				# Ждать не будем: анимация через минуту уже не анимация.
				log.warning("animation.flood_wait", seconds=e.seconds)
				return
			except RPCError as e:
				# Например, сообщение удалили посреди анимации.
				log.warning("animation.edit_failed", error=e.message)
				return
			previous = frame
