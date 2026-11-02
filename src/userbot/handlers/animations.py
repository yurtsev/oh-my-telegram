import re

from telethon import TelegramClient, events

from src.userbot.services.animations import AnimationService
from src.userbot.texts.animations import MOON_PHASES


class UserbotAnimationHandlers:
	"""Анимации работают в любом чате: личка, группы, «Избранное»."""

	def __init__(self, animations: AnimationService) -> None:
		self.animations = animations

	async def attach(self, client: TelegramClient) -> None:
		client.add_event_handler(
			self.animations.typewriter,
			events.NewMessage(
				outgoing=True,
				pattern=re.compile(
					r"^!type\s+(.+)$", re.IGNORECASE | re.DOTALL
				),
			),
		)
		client.add_event_handler(
			self.animations.moon,
			events.NewMessage(
				outgoing=True,
				pattern=re.compile(f"^!({'|'.join(MOON_PHASES)})$"),
			),
		)
		client.add_event_handler(
			self.animations.hearts,
			events.NewMessage(
				outgoing=True,
				# ❤️ с вариационным селектором и без — клавиатуры шлют по-разному.
				pattern=re.compile("^!❤️?$"),
			),
		)
