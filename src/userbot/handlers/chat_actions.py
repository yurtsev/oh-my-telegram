import re

from telethon import TelegramClient, events

from src.userbot.services.chat_actions import ChatActionService


class UserbotChatActionHandlers:
	"""Фейковые действия и !stop — в любом чате."""

	def __init__(self, actions: ChatActionService) -> None:
		self.actions = actions

	async def attach(self, client: TelegramClient) -> None:
		names = "|".join(ChatActionService.ACTIONS)
		client.add_event_handler(
			self.actions.fake_action,
			events.NewMessage(
				outgoing=True,
				pattern=re.compile(
					rf"^!({names})(?:\s+(\d+\s*[a-zа-яё]+))?$", re.IGNORECASE
				),
			),
		)
		client.add_event_handler(
			self.actions.stop,
			events.NewMessage(
				outgoing=True,
				pattern=re.compile(r"^!stop$", re.IGNORECASE),
			),
		)
